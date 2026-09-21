from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from models.disk_info import DiskInfo


class DiskInfoWidget(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    
    def __init__(self, disk_info: DiskInfo, parent=None):
        super().__init__(parent)
        
        self._disk_info = disk_info
        self._is_selected = False
        self._is_hovered = False
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self.setFixedHeight(70)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        self._name_label = QLabel(self._disk_info.display_name)
        self._name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
        layout.addWidget(self._name_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        size_text = f"{self._disk_info.formatted_free} / {self._disk_info.formatted_total}"
        self._size_label = QLabel(size_text)
        self._size_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        info_layout.addWidget(self._size_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(int(self._disk_info.usage_percentage))
        self._update_progress_color()
        info_layout.addWidget(self._progress_bar)
        
        layout.addLayout(info_layout)
    
    def _update_progress_color(self):
        percentage = self._disk_info.usage_percentage
        
        if percentage < 70:
            color = "#107C10"
        elif percentage < 90:
            color = "#FFB900"
        else:
            color = "#D83B01"
        
        style = f"""
            QProgressBar {{
                border: none;
                background-color: #E5E5E5;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """
        self._progress_bar.setStyleSheet(style)
    
    def _apply_styles(self):
        self._update_style()
    
    def _update_style(self):
        if self._is_selected:
            bg_color = "#E5F1FB"
            border_color = "#0078D4"
        elif self._is_hovered:
            bg_color = "#F5F5F5"
            border_color = "#E5E5E5"
        else:
            bg_color = "#FFFFFF"
            border_color = "#E5E5E5"
        
        style = f"""
            DiskInfoWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: #000000;
                background: transparent;
            }}
        """
        self.setStyleSheet(style)
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._update_style()
        self.update()
    
    def is_selected(self) -> bool:
        return self._is_selected
    
    def get_disk_info(self) -> DiskInfo:
        return self._disk_info
    
    def enterEvent(self, event):
        self._is_hovered = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self._is_selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = QPen(QColor("#0078D4"), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            rect = self.rect().adjusted(1, 1, -1, -1)
            painter.drawRoundedRect(rect, 8, 8)