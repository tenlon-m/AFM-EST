from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QStackedWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from .breadcrumb import BreadcrumbNavigation
from .path_completer import PathCompleter
from models.history import HistoryManager
from services.bookmark_manager import BookmarkManager


class AddressBar(QWidget):
    path_navigated = Signal(str)
    bookmark_added = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_path: Optional[str] = None
        self._is_edit_mode = False
        self._history_manager = HistoryManager()
        self._bookmark_manager = BookmarkManager()
        
        self._setup_ui()
        self._connect_signals()
        self._apply_styles()
        
        self._load_history()
        self.setAcceptDrops(True)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self._stack = QStackedWidget()
        
        self._breadcrumb = BreadcrumbNavigation()
        self._stack.addWidget(self._breadcrumb)
        
        self._line_edit = QLineEdit()
        self._line_edit.setFont(QFont("Segoe UI", 9))
        self._line_edit.setPlaceholderText("输入路径...")
        self._stack.addWidget(self._line_edit)
        
        layout.addWidget(self._stack)
        
        self._completer = PathCompleter(self._line_edit)
        self._line_edit.setCompleter(self._completer)
        
        self._go_button = QPushButton("→")
        self._go_button.setFixedSize(28, 28)
        self._go_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._go_button)
    
    def _connect_signals(self):
        self._breadcrumb.path_navigated.connect(self._on_breadcrumb_navigated)
        self._line_edit.returnPressed.connect(self._on_return_pressed)
        self._line_edit.textChanged.connect(self._on_text_changed)
        self._go_button.clicked.connect(self._on_go_clicked)
    
    def _apply_styles(self):
        style = """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: "Segoe UI";
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #0078D4;
            }
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #E5E5E5;
            }
            QPushButton:pressed {
                background-color: #D5D5D5;
            }
        """
        self.setStyleSheet(style)
    
    def _load_history(self) -> None:
        self._history_manager.load("config/history.json")
        history_paths = [item.path for item in self._history_manager.get_all()]
        self._completer.set_history(history_paths)
    
    def set_path(self, path: str) -> None:
        path_obj = Path(path)
        absolute_path = str(path_obj.absolute())
        
        if absolute_path == self._current_path:
            return
        
        self._current_path = absolute_path
        self._breadcrumb.set_path(absolute_path)
        self._line_edit.setText(absolute_path)
        
        self._history_manager.add(absolute_path)
        self._save_history()
        
        if not self._is_edit_mode:
            self._stack.setCurrentWidget(self._breadcrumb)
    
    def _save_history(self) -> None:
        self._history_manager.save("config/history.json")
    
    def switch_to_edit_mode(self) -> None:
        self._is_edit_mode = True
        self._stack.setCurrentWidget(self._line_edit)
        self._line_edit.setFocus()
        self._line_edit.selectAll()
    
    def switch_to_navigation_mode(self) -> None:
        self._is_edit_mode = False
        self._stack.setCurrentWidget(self._breadcrumb)
    
    def _on_breadcrumb_navigated(self, path: str) -> None:
        self.path_navigated.emit(path)
    
    def _on_return_pressed(self) -> None:
        path = self._line_edit.text().strip()
        if path:
            self._navigate_to_path(path)
    
    def _on_text_changed(self, text: str) -> None:
        self._completer.update_completions(text)
    
    def _on_go_clicked(self) -> None:
        if self._is_edit_mode:
            path = self._line_edit.text().strip()
            if path:
                self._navigate_to_path(path)
        else:
            self.switch_to_edit_mode()
    
    def _navigate_to_path(self, path: str) -> None:
        path_obj = Path(path)
        
        if path_obj.exists():
            absolute_path = str(path_obj.absolute())
            self.set_path(absolute_path)
            self.path_navigated.emit(absolute_path)
            self.switch_to_navigation_mode()
    
    def get_current_path(self) -> Optional[str]:
        return self._current_path
    
    def add_bookmark(self) -> bool:
        if self._current_path:
            return self._bookmark_manager.add(self._current_path)
        return False
    
    def remove_bookmark(self) -> bool:
        if self._current_path:
            return self._bookmark_manager.remove(self._current_path)
        return False
    
    def is_bookmarked(self) -> bool:
        if self._current_path:
            return self._bookmark_manager.exists(self._current_path)
        return False
    
    def get_history(self) -> List[str]:
        return [item.path for item in self._history_manager.get_all()]
    
    def get_bookmarks(self) -> List[dict]:
        return self._bookmark_manager.get_all()
    
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            if self._is_edit_mode:
                self.switch_to_navigation_mode()
                if self._current_path:
                    self._line_edit.setText(self._current_path)
        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            self.switch_to_edit_mode()
        else:
            super().keyPressEvent(event)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_dir():
                self._navigate_to_path(path)
    
    def focusInEvent(self, event) -> None:
        if not self._is_edit_mode:
            self._breadcrumb.setFocus()
        super().focusInEvent(event)