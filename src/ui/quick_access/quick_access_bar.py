from typing import List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction

from models.quick_access import QuickAccessItem
from services.quick_access_manager import QuickAccessManager
from .quick_access_item import QuickAccessItemWidget


class QuickAccessBar(QWidget):
    folder_accessed = Signal(str)
    item_pinned = Signal(str)
    item_unpinned = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._manager = QuickAccessManager()
        self._item_widgets: List[QuickAccessItemWidget] = []
        
        self._setup_ui()
        self._apply_styles()
        self._rebuild_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header = QLabel("快速访问")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setFixedHeight(28)
        header.setIndent(8)
        layout.addWidget(header)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(2)
        
        scroll_area.setWidget(self._container)
        layout.addWidget(scroll_area)
    
    def _apply_styles(self):
        style = """
            QLabel {
                background-color: #F5F5F5;
                color: #000000;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #C5C5C5;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A5A5A5;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
        """
        self.setStyleSheet(style)
    
    def _rebuild_ui(self) -> None:
        for widget in self._item_widgets:
            widget.deleteLater()
        self._item_widgets.clear()
        
        items = self._manager.get_sorted_items()
        
        for item in items:
            widget = QuickAccessItemWidget(item, self)
            widget.clicked.connect(lambda checked, w=widget: self._on_item_clicked(w))
            widget.double_clicked.connect(lambda w=widget: self._on_item_double_clicked(w))
            widget.context_menu_requested.connect(lambda w=widget: self._show_context_menu(w))
            
            self._container_layout.addWidget(widget)
            self._item_widgets.append(widget)
        
        self._container_layout.addStretch()
    
    def _on_item_clicked(self, widget: QuickAccessItemWidget) -> None:
        pass
    
    def _on_item_double_clicked(self, widget: QuickAccessItemWidget) -> None:
        item = widget.get_item()
        if item.is_valid:
            self.folder_accessed.emit(item.path)
    
    def _show_context_menu(self, widget: QuickAccessItemWidget) -> None:
        item = widget.get_item()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background-color: #E5E5E5;
            }
        """)
        
        if item.is_pinned:
            unpin_action = QAction("取消固定", self)
            unpin_action.triggered.connect(lambda: self._unpin_item(item.path))
            menu.addAction(unpin_action)
        else:
            pin_action = QAction("固定", self)
            pin_action.triggered.connect(lambda: self._pin_item(item.path))
            menu.addAction(pin_action)
        
        remove_action = QAction("删除", self)
        remove_action.triggered.connect(lambda: self._remove_item(item.path))
        menu.addAction(remove_action)
        
        if not item.is_pinned:
            menu.addSeparator()
            clear_action = QAction("清除最近记录", self)
            clear_action.triggered.connect(self._clear_recent)
            menu.addAction(clear_action)
        
        menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
    
    def _pin_item(self, path: str) -> None:
        self._manager.pin_folder(path)
        self._rebuild_ui()
        self.item_pinned.emit(path)
    
    def _unpin_item(self, path: str) -> None:
        self._manager.unpin_folder(path)
        self._rebuild_ui()
        self.item_unpinned.emit(path)
    
    def _remove_item(self, path: str) -> None:
        self._manager.remove_item(path)
        self._rebuild_ui()
    
    def _clear_recent(self) -> None:
        self._manager.clear_recent()
        self._rebuild_ui()
    
    def add_access(self, path: str) -> None:
        self._manager.add_access(path)
        self._rebuild_ui()
    
    def pin_folder(self, path: str) -> None:
        self._manager.pin_folder(path)
        self._rebuild_ui()
    
    def unpin_folder(self, path: str) -> None:
        self._manager.unpin_folder(path)
        self._rebuild_ui()
    
    def is_pinned(self, path: str) -> bool:
        return self._manager.is_pinned(path)
    
    def get_items(self) -> List[QuickAccessItem]:
        return self._manager.get_sorted_items()
    
    def refresh(self) -> None:
        self._rebuild_ui()