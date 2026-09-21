from typing import List, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame
from PySide6.QtCore import Qt, Signal

from models.disk_info import DiskInfo
from .disk_info_widget import DiskInfoWidget


class DiskPopupWidget(QWidget):
    disk_selected = Signal(DiskInfo)
    escape_pressed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._disk_widgets: List[DiskInfoWidget] = []
        self._selected_index = -1
        self._disks: List[DiskInfo] = []
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        container = QWidget()
        container.setObjectName("popupContainer")
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(8, 8, 8, 8)
        self._container_layout.setSpacing(4)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setMinimumWidth(280)
        scroll_area.setMaximumWidth(320)
        scroll_area.setMinimumHeight(100)
        scroll_area.setMaximumHeight(400)
        
        main_layout.addWidget(scroll_area)
        
        self.setFocusPolicy(Qt.StrongFocus)
    
    def _apply_styles(self):
        style = """
            #popupContainer {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E5;
                border-radius: 8px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
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
                border: none;
                background: none;
                height: 0px;
            }
        """
        self.setStyleSheet(style)
    
    def set_disks(self, disks: List[DiskInfo]) -> None:
        self._disks = disks
        
        for widget in self._disk_widgets:
            widget.deleteLater()
        self._disk_widgets.clear()
        
        for disk in disks:
            widget = DiskInfoWidget(disk, self)
            # 使用默认参数捕获widget，避免闭包问题
            widget.clicked.connect(lambda checked=False, w=widget: self._on_disk_clicked(w))
            widget.double_clicked.connect(lambda checked=False, w=widget: self._on_disk_double_clicked(w))
            self._container_layout.addWidget(widget)
            self._disk_widgets.append(widget)
        
        if self._disk_widgets:
            self._select_index(0)
        
        self._adjust_size()
    
    def _adjust_size(self) -> None:
        if not self._disk_widgets:
            self.setFixedSize(280, 100)
            return
        
        total_height = 16
        for widget in self._disk_widgets:
            total_height += widget.height() + 4
        
        height = min(total_height, 400)
        self.setFixedSize(300, height)
    
    def _on_disk_clicked(self, widget: DiskInfoWidget) -> None:
        index = self._disk_widgets.index(widget)
        self._select_index(index)
    
    def _on_disk_double_clicked(self, widget: DiskInfoWidget) -> None:
        disk_info = widget.get_disk_info()
        self.disk_selected.emit(disk_info)
        self.hide()
    
    def _select_index(self, index: int) -> None:
        if not self._disk_widgets:
            return
        
        if index < 0:
            index = len(self._disk_widgets) - 1
        elif index >= len(self._disk_widgets):
            index = 0
        
        for i, widget in enumerate(self._disk_widgets):
            widget.set_selected(i == index)
        
        self._selected_index = index
    
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Up:
            self._select_index(self._selected_index - 1)
        elif event.key() == Qt.Key_Down:
            self._select_index(self._selected_index + 1)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if 0 <= self._selected_index < len(self._disk_widgets):
                widget = self._disk_widgets[self._selected_index]
                disk_info = widget.get_disk_info()
                self.disk_selected.emit(disk_info)
                self.hide()
        elif event.key() == Qt.Key_Escape:
            self.escape_pressed.emit()
            self.hide()
        else:
            super().keyPressEvent(event)
    
    def show_popup(self, global_pos) -> None:
        self.move(global_pos)
        self.show()
        self.setFocus()
    
    def get_selected_disk(self) -> Optional[DiskInfo]:
        if 0 <= self._selected_index < len(self._disks):
            return self._disks[self._selected_index]
        return None