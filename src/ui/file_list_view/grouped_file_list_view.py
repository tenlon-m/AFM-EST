from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QCursor, QMenu, QAction

from models.theme_config import ThemeType
from ..theme.theme_manager import ThemeManager
from .icon_manager import IconManager

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class GroupedFileListView(QTreeWidget):
    item_activated = Signal(str)
    item_context_menu = Signal(str, object)
    selection_changed = Signal(list)
    group_mode_changed = Signal(str)
    
    GROUP_BY_NONE = "none"
    GROUP_BY_TYPE = "type"
    GROUP_BY_DATE = "date"
    GROUP_BY_SIZE = "size"
    
    TYPE_GROUPS = {
        "文档": [".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf", ".odt", ".ods", ".odp"],
        "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff", ".tif"],
        "视频": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
        "音频": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".ape"],
        "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"],
        "代码": [".py", ".js", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".php", ".html", ".css", ".json", ".xml", ".yaml", ".yml"],
        "可执行文件": [".exe", ".msi", ".bat", ".cmd", ".sh", ".bash", ".app", ".dmg", ".deb", ".rpm"],
    }
    
    DATE_GROUPS = [
        ("今天", lambda dt: dt.date() == datetime.now().date()),
        ("昨天", lambda dt: dt.date() == (datetime.now() - timedelta(days=1)).date()),
        ("本周", lambda dt: dt.date() >= (datetime.now() - timedelta(days=datetime.now().weekday())).date()),
        ("本月", lambda dt: dt.month == datetime.now().month and dt.year == datetime.now().year),
        ("更早", lambda dt: True),
    ]
    
    SIZE_GROUPS = [
        ("极小 (< 1KB)", 0, 1024),
        ("小 (1KB - 100KB)", 1024, 102400),
        ("中 (100KB - 1MB)", 102400, 1048576),
        ("大 (1MB - 100MB)", 1048576, 104857600),
        ("极大 (> 100MB)", 104857600, float('inf')),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._group_mode = self.GROUP_BY_NONE
        self._current_path: Optional[str] = None
        self._files: List[Dict[str, Any]] = []
        self._theme_manager = ThemeManager()
        self._icon_manager = IconManager()
        self._show_hidden_files = False
        
        self._init_ui()
        self._connect_signals()
        self._apply_theme()
    
    def _init_ui(self):
        self.setHeaderLabels(["名称", "大小", "类型", "修改日期"])
        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(True)
        self.setIndentation(20)
        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(150)
        header.resizeSection(0, 250)
        header.resizeSection(1, 100)
        header.resizeSection(2, 100)
        header.resizeSection(3, 150)
    
    def _connect_signals(self):
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
    
    def _apply_theme(self):
        theme = self._theme_manager.get_current_theme()
        colors = theme.colors
        from PySide6.QtGui import QColor
        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, QColor(colors.background))
        palette.setColor(palette.ColorRole.Text, QColor(colors.text_primary))
        palette.setColor(palette.ColorRole.Highlight, QColor(colors.accent))
        palette.setColor(palette.ColorRole.HighlightedText, QColor(colors.text_on_accent))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QTreeWidget {{ background-color: {colors.background}; color: {colors.text_primary}; border: none; }}
            QTreeWidget::item:hover {{ background-color: {colors.hover_background}; }}
            QTreeWidget::item:selected {{ background-color: {colors.accent}; color: {colors.text_on_accent}; }}
            QHeaderView::section {{ background-color: {colors.surface}; color: {colors.text_primary}; border: none; padding: 4px; }}
        """)
    
    def set_group_mode(self, mode: str) -> None:
        if self._group_mode == mode:
            return
        
        self._group_mode = mode
        logger.info(f"分组模式已设置为: {mode}")
        
        if self._files:
            self._refresh_view()
        
        self.group_mode_changed.emit(mode)
    
    def get_group_mode(self) -> str:
        return self._group_mode
    
    def set_path(self, path: str) -> None:
        self._current_path = path
        self._load_files()
        self._refresh_view()
    
    def get_current_path(self) -> Optional[str]:
        return self._current_path
    
    def _load_files(self) -> None:
        if not self._current_path or not os.path.isdir(self._current_path):
            self._files = []
            return
        
        self._files = []
        
        try:
            for entry in os.scandir(self._current_path):
                if not self._show_hidden_files and entry.name.startswith('.'):
                    continue
                
                try:
                    stat = entry.stat()
                    file_info = {
                        'name': entry.name,
                        'path': entry.path,
                        'is_dir': entry.is_dir(),
                        'size': stat.st_size if not entry.is_dir() else 0,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'type': self._get_file_type(entry),
                        'ext': Path(entry.name).suffix.lower(),
                    }
                    self._files.append(file_info)
                except (OSError, PermissionError) as e:
                    logger.warning(f"无法访问文件 {entry.path}: {e}")
                    continue
        except (OSError, PermissionError) as e:
            logger.error(f"无法读取目录 {self._current_path}: {e}")
            self._files = []
    
    def _get_file_type(self, entry) -> str:
        if entry.is_dir():
            return "文件夹"
        
        ext = Path(entry.name).suffix.lower()
        
        for type_name, extensions in self.TYPE_GROUPS.items():
            if ext in extensions:
                return type_name
        
        return "其他"
    
    def _refresh_view(self) -> None:
        self.clear()
        
        if not self._files:
            return
        
        if self._group_mode == self.GROUP_BY_NONE:
            self._display_without_grouping()
        elif self._group_mode == self.GROUP_BY_TYPE:
            self._display_grouped_by_type()
        elif self._group_mode == self.GROUP_BY_DATE:
            self._display_grouped_by_date()
        elif self._group_mode == self.GROUP_BY_SIZE:
            self._display_grouped_by_size()
        
        self.expandAll()
    
    def _display_without_grouping(self) -> None:
        for file_info in self._files:
            item = self._create_file_item(file_info)
            self.addTopLevelItem(item)
    
    def _display_grouped_by_type(self) -> None:
        type_groups: Dict[str, List[Dict]] = {}
        
        for file_info in self._files:
            file_type = file_info['type']
            if file_type not in type_groups:
                type_groups[file_type] = []
            type_groups[file_type].append(file_info)
        
        sorted_types = sorted(type_groups.items(), key=lambda x: x[0])
        
        for type_name, files in sorted_types:
            group_item = QTreeWidgetItem([f"{type_name} ({len(files)}项)", "", "", ""])
            group_item.setData(0, Qt.UserRole, "group_header")
            group_item.setData(0, Qt.UserRole + 1, type_name)
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            self.addTopLevelItem(group_item)
            
            for file_info in sorted(files, key=lambda x: x['name'].lower()):
                file_item = self._create_file_item(file_info)
                group_item.addChild(file_item)
    
    def _display_grouped_by_date(self) -> None:
        date_groups: Dict[str, List[Dict]] = {}
        
        for file_info in self._files:
            modified = file_info['modified']
            
            for group_name, check_func in self.DATE_GROUPS:
                if check_func(modified):
                    if group_name not in date_groups:
                        date_groups[group_name] = []
                    date_groups[group_name].append(file_info)
                    break
        
        for group_name, check_func in self.DATE_GROUPS:
            if group_name in date_groups:
                files = date_groups[group_name]
                
                group_item = QTreeWidgetItem([f"{group_name} ({len(files)}项)", "", "", ""])
                group_item.setData(0, Qt.UserRole, "group_header")
                group_item.setData(0, Qt.UserRole + 1, group_name)
                group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
                
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                
                self.addTopLevelItem(group_item)
                
                sorted_files = sorted(files, key=lambda x: x['modified'], reverse=True)
                for file_info in sorted_files:
                    file_item = self._create_file_item(file_info)
                    group_item.addChild(file_item)
    
    def _display_grouped_by_size(self) -> None:
        size_groups: Dict[str, List[Dict]] = {}
        
        for file_info in self._files:
            size = file_info['size']
            
            for group_name, min_size, max_size in self.SIZE_GROUPS:
                if min_size <= size < max_size:
                    if group_name not in size_groups:
                        size_groups[group_name] = []
                    size_groups[group_name].append(file_info)
                    break
        
        for group_name, min_size, max_size in self.SIZE_GROUPS:
            if group_name in size_groups:
                files = size_groups[group_name]
                
                group_item = QTreeWidgetItem([f"{group_name} ({len(files)}项)", "", "", ""])
                group_item.setData(0, Qt.UserRole, "group_header")
                group_item.setData(0, Qt.UserRole + 1, group_name)
                group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
                
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                
                self.addTopLevelItem(group_item)
                
                sorted_files = sorted(files, key=lambda x: x['size'], reverse=True)
                for file_info in sorted_files:
                    file_item = self._create_file_item(file_info)
                    group_item.addChild(file_item)
    
    def _create_file_item(self, file_info: Dict[str, Any]) -> QTreeWidgetItem:
        name = file_info['name']
        size = self._format_size(file_info['size']) if not file_info['is_dir'] else ""
        file_type = file_info['type']
        modified = file_info['modified'].strftime("%Y-%m-%d %H:%M:%S")
        
        item = QTreeWidgetItem([name, size, file_type, modified])
        item.setData(0, Qt.UserRole, "file_item")
        item.setData(0, Qt.UserRole + 1, file_info['path'])
        item.setData(0, Qt.UserRole + 2, file_info['is_dir'])
        
        icon = self._get_file_icon(file_info)
        if icon:
            item.setIcon(0, icon)
        
        return item
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                if unit == 'B':
                    return f"{size}{unit}"
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}PB"
    
    def _get_file_icon(self, file_info: Dict[str, Any]) -> Optional[QIcon]:
        if file_info['is_dir']:
            return self._icon_manager.get_folder_icon()
        else:
            return self._icon_manager.get_file_icon(file_info['ext'])
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        item_type = item.data(0, Qt.UserRole)
        
        if item_type == "file_item":
            path = item.data(0, Qt.UserRole + 1)
            if path:
                self.item_activated.emit(path)
    
    def _on_selection_changed(self) -> None:
        selected_paths = []
        
        for item in self.selectedItems():
            item_type = item.data(0, Qt.UserRole)
            if item_type == "file_item":
                path = item.data(0, Qt.UserRole + 1)
                if path:
                    selected_paths.append(path)
        
        self.selection_changed.emit(selected_paths)
    
    def _on_context_menu(self, position) -> None:
        item = self.itemAt(position)
        
        if not item:
            return
        
        item_type = item.data(0, Qt.UserRole)
        
        if item_type == "file_item":
            path = item.data(0, Qt.UserRole + 1)
            if path:
                self.item_context_menu.emit(path, QCursor.pos())
        elif item_type == "group_header":
            menu = QMenu(self)
            
            expand_all_action = QAction("展开所有分组", self)
            expand_all_action.triggered.connect(self.expandAll)
            menu.addAction(expand_all_action)
            
            collapse_all_action = QAction("折叠所有分组", self)
            collapse_all_action.triggered.connect(self.collapseAll)
            menu.addAction(collapse_all_action)
            
            menu.exec(QCursor.pos())
    
    def _on_theme_changed(self, theme_type: ThemeType) -> None:
        self._apply_theme()
    
    def set_show_hidden_files(self, show: bool) -> None:
        if self._show_hidden_files != show:
            self._show_hidden_files = show
            if self._current_path:
                self._load_files()
                self._refresh_view()
    
    def get_selected_paths(self) -> List[str]:
        selected_paths = []
        for item in self.selectedItems():
            item_type = item.data(0, Qt.UserRole)
            if item_type == "file_item":
                path = item.data(0, Qt.UserRole + 1)
                if path:
                    selected_paths.append(path)
        return selected_paths
    
    def refresh(self) -> None:
        if self._current_path:
            self._load_files()
            self._refresh_view()
    
    def expand_all_groups(self) -> None:
        self.expandAll()
    
    def collapse_all_groups(self) -> None:
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.data(0, Qt.UserRole) == "group_header":
                item.setExpanded(False)