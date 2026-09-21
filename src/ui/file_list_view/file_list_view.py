from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListView, QAbstractItemView,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QModelIndex, QSize, QTimer, QElapsedTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction

from models.view_config import ViewMode, IconSize
from ..theme.theme_manager import ThemeManager
from .file_list_delegate import FileListDelegate
from .virtual_scroller import VirtualScroller
from .icon_manager import IconManager
from services.thumbnail_loader import ThumbnailLoader
from services.thumbnail_cache import ThumbnailCache

try:
    from core.performance_decorator import monitor_performance
    HAS_PERFORMANCE_MONITOR = True
except ImportError:
    HAS_PERFORMANCE_MONITOR = False
    
    def monitor_performance(name):
        def decorator(func):
            return func
        return decorator

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger


class ModernFileListView(QWidget):
    item_activated = Signal(str)
    item_context_menu = Signal(str, object)
    view_mode_changed = Signal(ViewMode)
    selection_changed = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._view_mode = ViewMode.DETAILS
        self._icon_size = IconSize.MEDIUM
        self._theme_manager = ThemeManager()
        self._icon_manager = IconManager()
        self._thumbnail_cache = ThumbnailCache()
        self._thumbnail_loader = ThumbnailLoader(self._thumbnail_cache)
        self._virtual_scroller = VirtualScroller()
        self._logger = _logger
        
        self._model = QStandardItemModel(self)
        self._current_path: Optional[str] = None
        
        self._render_timer = QElapsedTimer()
        self._last_scroll_position = 0
        self._preserve_scroll_on_refresh = False
        
        self._init_ui()
        self._connect_signals()
        self._apply_theme()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._list_view = QListView(self)
        self._list_view.setModel(self._model)
        self._list_view.setItemDelegate(FileListDelegate(self))
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._list_view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        layout.addWidget(self._list_view)
        
        self._update_view_mode()
    
    def _connect_signals(self):
        self._list_view.activated.connect(self._on_item_activated)
        self._list_view.customContextMenuRequested.connect(self._on_context_menu)
        self._list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        
        self._virtual_scroller.range_changed.connect(self._on_visible_range_changed)
        
        self._thumbnail_loader.loaded.connect(self._on_thumbnail_loaded)
    
    def set_view_mode(self, mode: ViewMode) -> None:
        if self._view_mode == mode:
            return
        
        self._preserve_scroll_on_refresh = True
        self._last_scroll_position = self._list_view.verticalScrollBar().value()
        
        self._view_mode = mode
        self._update_view_mode()
        self.view_mode_changed.emit(mode)
        
        QTimer.singleShot(50, self._restore_scroll_position)
    
    def get_view_mode(self) -> ViewMode:
        return self._view_mode
    
    def set_icon_size(self, size: IconSize) -> None:
        self._icon_size = size
        delegate = self._list_view.itemDelegate()
        if isinstance(delegate, FileListDelegate):
            delegate.set_icon_size(size)
        
        self._list_view.setModel(None)
        self._list_view.setModel(self._model)
    
    def get_icon_size(self) -> IconSize:
        return self._icon_size
    
    def set_path(self, path: str) -> None:
        self._current_path = path
        self._load_directory(path)
    
    def get_current_path(self) -> Optional[str]:
        return self._current_path
    
    def refresh(self) -> None:
        if self._current_path:
            self._load_directory(self._current_path)
    
    def get_selected_items(self) -> List[str]:
        selected_indexes = self._list_view.selectedIndexes()
        items = []
        
        for index in selected_indexes:
            item = self._model.itemFromIndex(index)
            if item:
                path = item.data(Qt.UserRole)
                if path:
                    items.append(path)
        
        return items
    
    def select_all(self) -> None:
        self._list_view.selectAll()
    
    def clear_selection(self) -> None:
        self._list_view.clearSelection()
    
    def _update_view_mode(self):
        delegate = self._list_view.itemDelegate()
        if isinstance(delegate, FileListDelegate):
            delegate.set_view_mode(self._view_mode)
        
        if self._view_mode == ViewMode.DETAILS:
            self._list_view.setViewMode(QListView.ListMode)
            self._list_view.setGridSize(QSize())
        elif self._view_mode == ViewMode.ICONS:
            self._list_view.setViewMode(QListView.IconMode)
            icon_size = self._icon_size.value
            self._list_view.setGridSize(QSize(icon_size + 32, icon_size + 64))
        elif self._view_mode == ViewMode.THUMBNAILS:
            self._list_view.setViewMode(QListView.IconMode)
            icon_size = self._icon_size.value
            self._list_view.setGridSize(QSize(icon_size + 32, icon_size + 64))
        elif self._view_mode == ViewMode.LIST:
            self._list_view.setViewMode(QListView.ListMode)
            self._list_view.setGridSize(QSize())
        elif self._view_mode == ViewMode.TILE:
            self._list_view.setViewMode(QListView.ListMode)
            self._list_view.setGridSize(QSize())
        
        self._list_view.setModel(None)
        self._list_view.setModel(self._model)
    
    def _preload_thumbnails(self, items: List[Path]):
        """预加载缩略图（基于可见区域的懒加载）"""
        from .thumbnail_loader import ThumbnailPriority
        from PySide6.QtCore import QTimer
        
        if not hasattr(self, '_preload_timer'):
            self._preload_timer = QTimer()
            self._preload_timer.setSingleShot(True)
            self._preload_timer.timeout.connect(self._do_preload)
            self._pending_items = []
            self._loaded_paths = set()
        
        self._pending_items = items
        self._preload_timer.start(100)
    
    def _do_preload(self):
        """执行缩略图预加载（基于可见区域）"""
        from .thumbnail_loader import ThumbnailPriority
        
        if not self._pending_items:
            return
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'}
        
        visible_start, visible_end = self._virtual_scroller.get_visible_range()
        buffer_size = 10
        
        start_idx = max(0, visible_start - buffer_size)
        end_idx = min(len(self._pending_items), visible_end + buffer_size)
        
        for i in range(start_idx, end_idx):
            item_path = self._pending_items[i]
            if item_path.is_dir():
                continue
            
            ext = item_path.suffix.lower()
            if ext not in image_extensions:
                continue
            
            path_str = str(item_path)
            if path_str in self._loaded_paths:
                continue
            
            size = self._icon_size.value
            self._thumbnail_loader.load_thumbnail_async(
                path_str,
                QSize(size, size),
                ThumbnailPriority.BUFFER
            )
            self._loaded_paths.add(path_str)
    
    def _on_visible_range_changed(self, start: int, end: int):
        """可见范围变化时触发懒加载"""
        self._do_preload()
    
    def _clear_loaded_cache(self):
        """清空已加载缓存"""
        if hasattr(self, '_loaded_paths'):
            self._loaded_paths.clear()
    
    def _load_directory(self, path: str):
        self._clear_loaded_cache()
        self._model.clear()
        
        try:
            dir_path = Path(path)
            if not dir_path.exists() or not dir_path.is_dir():
                return
            
            items = list(dir_path.iterdir())
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item_path in items:
                item = QStandardItem(item_path.name)
                item.setData(str(item_path), Qt.UserRole)
                item.setData(item_path.is_dir(), Qt.UserRole + 1)
                
                self._model.appendRow(item)
            
            self._virtual_scroller.set_item_count(len(items))
            
            self._preload_thumbnails(items)
        
        except PermissionError as e:
            self._logger.warning(f"权限不足，无法访问路径: {self._current_path}, 错误: {e}")
        except Exception as e:
            self._logger.error(f"加载文件列表失败: {e}")
    
    def _apply_theme(self):
        theme = self._theme_manager.get_current_theme()
        delegate = self._list_view.itemDelegate()
        
        if isinstance(delegate, FileListDelegate):
            from PySide6.QtGui import QColor
            colors = theme.colors
            
            hover_color = QColor(colors.hover_background)
            selected_color = QColor(colors.accent)
            text_color = QColor(colors.text_primary)
            
            delegate.set_colors(hover_color, selected_color, text_color)
            delegate.set_corner_radius(theme.corner_radius)
        
        self._list_view.setModel(None)
        self._list_view.setModel(self._model)
    
    def _on_item_activated(self, index: QModelIndex):
        item = self._model.itemFromIndex(index)
        if item:
            path = item.data(Qt.UserRole)
            if path:
                self.item_activated.emit(path)
    
    def _on_context_menu(self, pos):
        index = self._list_view.indexAt(pos)
        if not index.isValid():
            return
        
        item = self._model.itemFromIndex(index)
        if not item:
            return
        
        path = item.data(Qt.UserRole)
        if path:
            menu = QMenu(self)
            
            open_action = QAction("打开", self)
            open_action.triggered.connect(lambda: self.item_activated.emit(path))
            menu.addAction(open_action)
            
            menu.addSeparator()
            
            self.item_context_menu.emit(path, menu)
            
            menu.exec(self._list_view.mapToGlobal(pos))
    
    def _on_selection_changed(self, selected, deselected):
        selected_items = self.get_selected_items()
        self.selection_changed.emit(selected_items)
    
    def _on_theme_changed(self, theme_config):
        self._apply_theme()
    
    def _on_visible_range_changed(self, start: int, end: int):
        for row in range(start, min(end + 1, self._model.rowCount())):
            item = self._model.item(row)
            if item:
                path = item.data(Qt.UserRole)
                if path:
                    from pathlib import Path
                    item_path = Path(path)
                    if item_path.is_file() and not item.data(Qt.DecorationRole):
                        size = self._icon_size.value
                        self._thumbnail_loader.load_thumbnail_async(
                            str(item_path),
                            QSize(size, size),
                            1
                        )
    
    def _on_thumbnail_loaded(self, path: str, pixmap):
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.data(Qt.UserRole) == path:
                item.setData(pixmap, Qt.DecorationRole)
                break
    
    def _restore_scroll_position(self) -> None:
        if self._preserve_scroll_on_refresh:
            self._list_view.verticalScrollBar().setValue(self._last_scroll_position)
            self._preserve_scroll_on_refresh = False
    
    def get_performance_statistics(self) -> dict:
        return {
            'cache_stats': self._thumbnail_cache.get_statistics(),
            'scroller_stats': self._virtual_scroller.get_statistics(),
            'icon_cache_count': self._icon_manager.get_cached_icon_count(),
            'model_row_count': self._model.rowCount(),
        }
    
    @monitor_performance("file_list_cleanup")
    def cleanup(self):
        self._thumbnail_loader.shutdown()
        self._thumbnail_cache.clear()
        self._icon_manager.clear_cache()