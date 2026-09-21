#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 11风格面包屑导航组件
"""

from typing import List
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Signal

from .models.path_segment_info import PathSegmentInfo
from .root_node_widget import RootNodeWidget
from .path_segment_widget import PathSegmentWidget
from .platform_adapter import platform_adapter
from core.logger import logger


class Win11Breadcrumb(QWidget):
    """
    Windows 11风格面包屑导航组件
    显示路径层级：此电脑 > 本地磁盘 (C:) > Users > Administrator
    """
    
    path_changed = Signal(str)  # 路径变更信号
    disk_selected = Signal(str)  # 磁盘选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_path = ""
        self._segments: List[PathSegmentInfo] = []
        self._segment_widgets: List[QWidget] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 0, 6, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch()
        
        self.setObjectName("win11Breadcrumb")
    
    def build_from_path(self, path: str):
        """
        根据路径构建面包屑导航
        
        Args:
            path: 完整路径
        """
        self._current_path = path
        
        # 清除旧的组件
        self._clear_segments()
        
        # 解析路径为路径段
        self._segments = platform_adapter.parse_path_to_segments(path)
        
        # 构建UI
        self._build_ui()
    
    def _clear_segments(self):
        """清除路径段组件"""
        for widget in self._segment_widgets:
            widget.deleteLater()
        self._segment_widgets.clear()
    
    def _build_ui(self):
        """构建UI"""
        # 移除stretch
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        self._segment_widgets.clear()
        
        # 添加路径段
        for i, segment in enumerate(self._segments):
            if segment.is_root:
                # 根节点
                root_widget = RootNodeWidget(self)
                root_widget.set_label(segment.name)
                root_widget.clicked.connect(self._on_root_clicked)
                self._layout.addWidget(root_widget)
                self._segment_widgets.append(root_widget)
            else:
                # 添加分隔符
                separator = QLabel(">")
                separator.setObjectName("pathSeparator")
                separator.setStyleSheet("""
                    QLabel {
                        color: #999999;
                        background: transparent;
                        font-size: 9pt;
                    }
                """)
                self._layout.addWidget(separator)
                self._segment_widgets.append(separator)
                
                # 路径段
                segment_widget = PathSegmentWidget(self)
                segment_widget.set_text(segment.name)
                segment_widget.set_path(segment.path)
                
                # 最后一个路径段标记为当前路径
                is_last = (i == len(self._segments) - 1)
                segment_widget.set_current(is_last)
                
                segment_widget.clicked.connect(lambda checked=False, p=segment.path: self._on_segment_clicked(p))
                self._layout.addWidget(segment_widget)
                self._segment_widgets.append(segment_widget)
        
        # 添加stretch
        self._layout.addStretch()
    
    def _on_root_clicked(self):
        """根节点点击事件"""
        logger.info("根节点被点击，显示所有磁盘")
        self.disk_selected.emit("")
    
    def _on_segment_clicked(self, path: str):
        """
        路径段点击事件
        
        Args:
            path: 路径
        """
        logger.info(f"路径段被点击: {path}")
        self.path_changed.emit(path)
    
    def get_current_path(self) -> str:
        """获取当前路径"""
        return self._current_path
    
    def apply_theme(self, theme_name: str):
        """
        应用主题
        
        Args:
            theme_name: 主题名称
        """
        for widget in self._segment_widgets:
            if hasattr(widget, 'apply_theme'):
                widget.apply_theme(theme_name)