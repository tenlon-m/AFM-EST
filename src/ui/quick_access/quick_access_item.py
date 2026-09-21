
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models.quick_access import QuickAccessItem
from ..file_list_view.icon_manager import IconManager


class QuickAccessItemWidget(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    context_menu_requested = Signal()
    
    def __init__(self, item: QuickAccessItem, parent=None):
        super().__init__(parent)
        
        self._item = item
        self._icon_manager = IconManager()
        self._is_hovered = False
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        icon = self._icon_manager.get_folder_icon()
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setPixmap(icon.pixmap(20, 20))
        layout.addWidget(self._icon_label)
        
        self._name_label = QLabel(self._item.display_name)
        self._name_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self._name_label, 1)
        
        if self._item.is_pinned:
            pin_label = QLabel("📌")
            pin_label.setFixedSize(16, 16)
            layout.addWidget(pin_label)
        
        if not self._item.is_valid:
            self._name_label.setStyleSheet("color: #999999;")
    
    def _apply_styles(self):
        self._update_style()
    
    def _update_style(self):
        if self._is_hovered:
            bg_color = "#F5F5F5"
        else:
            bg_color = "transparent"
        
        style = f"""
            QuickAccessItemWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
            QLabel {{
                background: transparent;
            }}
        """
        self.setStyleSheet(style)
    
    def get_item(self) -> QuickAccessItem:
        return self._item
    
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
        elif event.button() == Qt.RightButton:
            self.context_menu_requested.emit()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)