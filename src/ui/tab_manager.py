from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QPushButton, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class TabManager(QWidget):
    tab_added = Signal(int, str)
    tab_removed = Signal(int)
    tab_switched = Signal(int)
    tab_path_changed = Signal(int, str)
    
    def __init__(self, parent=None, max_tabs: int = 10):
        super().__init__(parent)
        
        self._max_tabs = max_tabs
        self._tabs: Dict[int, dict] = {}
        self._current_tab_id = -1
        self._next_tab_id = 0
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._tab_bar_layout = QHBoxLayout()
        self._tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_bar_layout.setSpacing(2)
        
        self._tab_buttons: List[QPushButton] = []
        
        self._tab_bar_widget = QWidget()
        self._tab_bar_widget.setLayout(self._tab_bar_layout)
        layout.addWidget(self._tab_bar_widget)
        
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._content_widget)
    
    def add_tab(self, path: str = "", name: str = None) -> int:
        if len(self._tabs) >= self._max_tabs:
            logger.warning(f"已达到最大标签页数量: {self._max_tabs}")
            return -1
        
        tab_id = self._next_tab_id
        self._next_tab_id += 1
        
        if name is None:
            if path:
                import os
                name = os.path.basename(path) or path
            else:
                name = f"标签 {tab_id + 1}"
        
        self._tabs[tab_id] = {
            'id': tab_id,
            'name': name,
            'path': path,
            'widget': None
        }
        
        tab_button = QPushButton(name)
        tab_button.setCheckable(True)
        tab_button.clicked.connect(lambda checked, tid=tab_id: self._on_tab_clicked(tid))
        tab_button.setContextMenuPolicy(Qt.CustomContextMenu)
        tab_button.customContextMenuRequested.connect(lambda pos, tid=tab_id: self._show_tab_context_menu(pos, tid))
        
        self._tab_buttons.append(tab_button)
        self._tab_bar_layout.addWidget(tab_button)
        
        if len(self._tabs) == 1:
            self.switch_to_tab(tab_id)
        
        self.tab_added.emit(tab_id, path)
        logger.info(f"添加标签页: {name} (ID: {tab_id})")
        
        return tab_id
    
    def remove_tab(self, tab_id: int) -> bool:
        if tab_id not in self._tabs:
            return False
        
        if len(self._tabs) <= 1:
            logger.warning("至少保留一个标签页")
            return False
        
        tab_info = self._tabs[tab_id]
        index = list(self._tabs.keys()).index(tab_id)
        
        del self._tabs[tab_id]
        
        tab_button = self._tab_buttons[index]
        self._tab_bar_layout.removeWidget(tab_button)
        tab_button.deleteLater()
        del self._tab_buttons[index]
        
        if self._current_tab_id == tab_id:
            remaining_ids = list(self._tabs.keys())
            if remaining_ids:
                new_index = min(index, len(remaining_ids) - 1)
                self.switch_to_tab(remaining_ids[new_index])
        
        self.tab_removed.emit(tab_id)
        logger.info(f"移除标签页: {tab_info['name']} (ID: {tab_id})")
        
        return True
    
    def switch_to_tab(self, tab_id: int) -> bool:
        if tab_id not in self._tabs:
            return False
        
        self._current_tab_id = tab_id
        
        for i, button in enumerate(self._tab_buttons):
            button.setChecked(list(self._tabs.keys())[i] == tab_id)
        
        self.tab_switched.emit(tab_id)
        logger.info(f"切换到标签页: {self._tabs[tab_id]['name']} (ID: {tab_id})")
        
        return True
    
    def set_tab_path(self, tab_id: int, path: str) -> bool:
        if tab_id not in self._tabs:
            return False
        
        import os
        name = os.path.basename(path) or path
        
        self._tabs[tab_id]['path'] = path
        self._tabs[tab_id]['name'] = name
        
        index = list(self._tabs.keys()).index(tab_id)
        self._tab_buttons[index].setText(name)
        
        self.tab_path_changed.emit(tab_id, path)
        
        return True
    
    def get_current_tab_id(self) -> int:
        return self._current_tab_id
    
    def get_current_tab_path(self) -> str:
        if self._current_tab_id in self._tabs:
            return self._tabs[self._current_tab_id]['path']
        return ""
    
    def get_tab_count(self) -> int:
        return len(self._tabs)
    
    def get_all_tabs(self) -> List[dict]:
        return list(self._tabs.values())
    
    def _on_tab_clicked(self, tab_id: int):
        self.switch_to_tab(tab_id)
    
    def _show_tab_context_menu(self, pos, tab_id: int):
        menu = QMenu(self)
        
        close_action = menu.addAction("关闭")
        close_action.triggered.connect(lambda: self.remove_tab(tab_id))
        
        close_others_action = menu.addAction("关闭其他")
        close_others_action.triggered.connect(lambda: self._close_other_tabs(tab_id))
        
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self._rename_tab(tab_id))
        
        menu.exec(self.mapToGlobal(pos))
    
    def _close_other_tabs(self, keep_tab_id: int):
        tab_ids = list(self._tabs.keys())
        for tab_id in tab_ids:
            if tab_id != keep_tab_id:
                self.remove_tab(tab_id)
    
    def _rename_tab(self, tab_id: int):
        if tab_id not in self._tabs:
            return
        
        current_name = self._tabs[tab_id]['name']
        new_name, ok = QInputDialog.getText(
            self, "重命名标签", "新名称:", text=current_name
        )
        
        if ok and new_name:
            self._tabs[tab_id]['name'] = new_name
            index = list(self._tabs.keys()).index(tab_id)
            self._tab_buttons[index].setText(new_name)