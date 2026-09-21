from typing import Optional, List
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QSize

from models.disk_info import DiskInfo
from services.disk_info_provider import DiskInfoProvider
from .disk_popup import DiskPopupWidget


class DiskSelector(QWidget):
    disk_selected = Signal(DiskInfo)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_disk: Optional[DiskInfo] = None
        self._disks: List[DiskInfo] = []
        self._provider = DiskInfoProvider(self)
        self._popup: Optional[DiskPopupWidget] = None
        
        self._setup_ui()
        self._connect_signals()
        self._apply_styles()
        
        self._provider.get_disk_info_async()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self._button = QPushButton()
        self._button.setFixedHeight(28)
        self._button.setCursor(Qt.PointingHandCursor)
        self._button.setText("选择磁盘")
        layout.addWidget(self._button)
        
        self._popup = DiskPopupWidget(self)
    
    def _connect_signals(self):
        self._button.clicked.connect(self._show_popup)
        self._provider.disks_loaded.connect(self._on_disks_loaded)
        self._provider.load_error.connect(self._on_load_error)
        
        if self._popup:
            self._popup.disk_selected.connect(self._on_disk_selected)
            self._popup.escape_pressed.connect(self._hide_popup)
    
    def _apply_styles(self):
        style = """
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: "Segoe UI";
                font-size: 9pt;
                color: #000000;
                min-width: 80px;
                max-width: 150px;
            }
            QPushButton:hover {
                background-color: #E5E5E5;
                border: 1px solid #D5D5D5;
            }
            QPushButton:pressed {
                background-color: #D5D5D5;
            }
        """
        self.setStyleSheet(style)
    
    def _show_popup(self):
        if not self._popup:
            return
        
        button_rect = self._button.rect()
        global_pos = self.mapToGlobal(button_rect.bottomLeft())
        
        global_pos.setY(global_pos.y() + 2)
        
        self._popup.set_disks(self._disks)
        self._popup.show_popup(global_pos)
    
    def _hide_popup(self):
        if self._popup:
            self._popup.hide()
    
    def _on_disks_loaded(self, disks: List[DiskInfo]) -> None:
        self._disks = disks
        
        if disks and not self._current_disk:
            self._set_current_disk(disks[0])
    
    def _on_load_error(self, error: str) -> None:
        self._button.setText("加载失败")
    
    def _on_disk_selected(self, disk: DiskInfo) -> None:
        self._set_current_disk(disk)
        self.disk_selected.emit(disk)
    
    def _set_current_disk(self, disk: DiskInfo) -> None:
        self._current_disk = disk
        self._button.setText(disk.display_name)
    
    def set_disk(self, disk: DiskInfo) -> None:
        self._set_current_disk(disk)
    
    def get_current_disk(self) -> Optional[DiskInfo]:
        return self._current_disk
    
    def refresh_disks(self) -> None:
        self._provider.invalidate_cache()
        self._provider.get_disk_info_async()
    
    def set_button_width(self, width: int) -> None:
        self._button.setFixedWidth(width)
    
    def sizeHint(self) -> QSize:
        return QSize(120, 28)