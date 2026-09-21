from typing import List, Optional
from pathlib import Path

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal


class BreadcrumbNavigation(QWidget):
    path_navigated = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_path: Optional[str] = None
        self._segments: List[str] = []
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(0)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 4px 8px;
                font-family: "Segoe UI";
                font-size: 9pt;
                color: #000000;
            }
            QPushButton:hover {
                background-color: #E5E5E5;
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                color: #666666;
                font-size: 9pt;
            }
        """)
    
    def set_path(self, path: str) -> None:
        if path == self._current_path:
            return
        
        self._current_path = path
        self._segments = self._parse_path(path)
        self._rebuild_ui()
    
    def _parse_path(self, path: str) -> List[str]:
        path_obj = Path(path)
        parts = list(path_obj.parts)
        return parts
    
    def _rebuild_ui(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        accumulated_path = ""
        
        for i, segment in enumerate(self._segments):
            if i > 0:
                separator = QLabel("›")
                separator.setFixedWidth(16)
                separator.setAlignment(Qt.AlignCenter)
                self._layout.addWidget(separator)
            
            if i == 0 and len(segment) == 3 and segment[1] == ':':
                accumulated_path = segment
            elif segment == '/':
                accumulated_path = '/'
            else:
                if accumulated_path and accumulated_path != '/':
                    accumulated_path = str(Path(accumulated_path) / segment)
                else:
                    accumulated_path = segment
            
            button = QPushButton(segment)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked, p=accumulated_path: self._on_segment_clicked(p))
            
            self._layout.addWidget(button)
        
        self._layout.addStretch()
    
    def _on_segment_clicked(self, path: str) -> None:
        self.path_navigated.emit(path)
    
    def get_current_path(self) -> Optional[str]:
        return self._current_path
    
    def clear(self) -> None:
        self._current_path = None
        self._segments.clear()
        
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()