from typing import Dict
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt

from models.view_config import IconSize


class IconManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._icon_cache: Dict[str, QIcon] = {}
        self._rounded_cache: Dict[str, QIcon] = {}
        self._corner_radius = 8
        self._initialized = True
        
        self._preload_icons()
    
    def _preload_icons(self) -> None:
        pass
    
    def get_file_icon(self, file_path: str, size: IconSize = IconSize.MEDIUM) -> QIcon:
        path = Path(file_path)
        extension = path.suffix.lower()
        
        cache_key = f"file_{extension}_{size.value}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        icon = self._get_icon_for_extension(extension)
        icon = self.apply_rounded_corners(icon, size.value)
        
        self._icon_cache[cache_key] = icon
        return icon
    
    def get_folder_icon(self, size: IconSize = IconSize.MEDIUM) -> QIcon:
        cache_key = f"folder_{size.value}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        icon = self._create_folder_icon(size.value)
        icon = self.apply_rounded_corners(icon, size.value)
        
        self._icon_cache[cache_key] = icon
        return icon
    
    def _get_icon_for_extension(self, extension: str) -> QIcon:
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'}
        document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md'}
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs'}
        
        if extension in image_extensions:
            return QIcon.fromTheme("image-x-generic", QIcon())
        elif extension in video_extensions:
            return QIcon.fromTheme("video-x-generic", QIcon())
        elif extension in audio_extensions:
            return QIcon.fromTheme("audio-x-generic", QIcon())
        elif extension in document_extensions:
            return QIcon.fromTheme("text-x-generic", QIcon())
        elif extension in archive_extensions:
            return QIcon.fromTheme("package-x-generic", QIcon())
        elif extension in code_extensions:
            return QIcon.fromTheme("text-x-script", QIcon())
        else:
            return QIcon.fromTheme("text-x-generic", QIcon())
    
    def _create_folder_icon(self, size: int) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = QColor("#FFB900")
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        margin = size // 8
        folder_width = size - 2 * margin
        folder_height = size - 2 * margin
        tab_height = folder_height // 4
        
        painter.drawRoundedRect(margin, margin + tab_height, folder_width, folder_height - tab_height, 4, 4)
        
        painter.drawRect(margin, margin, folder_width // 2, tab_height)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def apply_rounded_corners(self, icon: QIcon, size: int) -> QIcon:
        if not icon or icon.isNull():
            return icon
        
        cache_key = f"{icon.cacheKey()}_{size}_{self._corner_radius}"
        if cache_key in self._rounded_cache:
            return self._rounded_cache[cache_key]
        
        pixmap = icon.pixmap(size, size)
        if pixmap.isNull():
            return icon
        
        rounded_pixmap = QPixmap(size, size)
        rounded_pixmap.fill(Qt.transparent)
        
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, size, size, self._corner_radius, self._corner_radius)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        rounded_icon = QIcon(rounded_pixmap)
        self._rounded_cache[cache_key] = rounded_icon
        
        return rounded_icon
    
    def set_corner_radius(self, radius: int) -> None:
        self._corner_radius = radius
        self._rounded_cache.clear()
    
    def clear_cache(self) -> None:
        self._icon_cache.clear()
        self._rounded_cache.clear()
    
    def get_cached_icon_count(self) -> int:
        return len(self._icon_cache)