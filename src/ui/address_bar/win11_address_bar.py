#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 11风格地址栏主组件
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QStackedWidget, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from .win11_breadcrumb import Win11Breadcrumb
from .models.navigation_mode import NavigationMode
from core.logger import logger


class Win11AddressBar(QWidget):
    """
    Windows 11风格地址栏主组件
    支持面包屑导航和路径编辑两种模式
    """
    
    path_changed = Signal(str)  # 路径变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_path = ""
        self._mode = NavigationMode.BREADCRUMB
        
        self._setup_ui()
        self._connect_signals()
        self._apply_style()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 使用StackedWidget切换模式
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        
        # 面包屑导航模式（带滚动条）
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        self._breadcrumb = Win11Breadcrumb(self)
        self._scroll_area.setWidget(self._breadcrumb)
        self._stack.addWidget(self._scroll_area)
        
        # 路径编辑模式
        self._path_edit = QLineEdit()
        self._path_edit.setObjectName("pathEdit")
        self._stack.addWidget(self._path_edit)
        
        # 设置组件属性
        self.setObjectName("win11AddressBar")
        self.setFixedHeight(29)  # 增加20%高度（24 * 1.2 ≈ 29）
    
    def _connect_signals(self):
        """连接信号"""
        self._breadcrumb.path_changed.connect(self._on_breadcrumb_path_changed)
        self._breadcrumb.disk_selected.connect(self._on_disk_selected)
        
        self._path_edit.returnPressed.connect(self._on_path_edit_return)
        self._path_edit.installEventFilter(self)
    
    def _apply_style(self):
        """应用样式"""
        self.set_focus_style(False)
    
    def set_focus_style(self, has_focus: bool):
        """
        设置焦点样式（地址栏样式保持不变，由容器边框显示焦点）
        
        Args:
            has_focus: 是否有焦点
        """
        # 地址栏样式保持不变
        main_style = """
            #win11AddressBar {
                background-color: #F8F8F8;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
            }
        """
        scroll_style = """
            QScrollArea {
                background-color: #F8F8F8;
                border: none;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: #C0C0C0;
                border-radius: 2px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #A0A0A0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """
        
        self.setStyleSheet(main_style)
        if hasattr(self, '_scroll_area'):
            self._scroll_area.setStyleSheet(scroll_style)
    
    def set_path(self, path: str):
        """
        设置当前路径
        
        Args:
            path: 路径
        """
        self._current_path = path
        self._breadcrumb.build_from_path(path)
        
        # 如果当前在编辑模式，也更新编辑框的内容
        if self._mode == NavigationMode.EDIT:
            self._path_edit.setText(path)
    
    def get_current_path(self) -> str:
        """获取当前路径"""
        return self._current_path
    
    def switch_to_edit_mode(self):
        """切换到编辑模式"""
        self._mode = NavigationMode.EDIT
        self._path_edit.setText(self._current_path)
        self._stack.setCurrentWidget(self._path_edit)
        self._path_edit.selectAll()
        self._path_edit.setFocus()
    
    def switch_to_breadcrumb_mode(self):
        """切换到面包屑模式"""
        if self._mode == NavigationMode.BREADCRUMB:
            return
        
        self._mode = NavigationMode.BREADCRUMB
        self._breadcrumb.build_from_path(self._current_path)
        
        # 找到scroll_area并设置为当前widget
        scroll_area = self._stack.widget(0)
        self._stack.setCurrentWidget(scroll_area)
        
        logger.info("切换到面包屑导航模式")
    
    def _on_breadcrumb_path_changed(self, path: str):
        """
        面包屑路径变更事件
        
        Args:
            path: 新路径
        """
        self._current_path = path
        self.path_changed.emit(path)
    
    def _on_disk_selected(self, disk_path: str):
        """
        磁盘选择事件 - 弹出磁盘选择器
        
        Args:
            disk_path: 磁盘路径（空字符串表示从根节点点击）
        """
        logger.info(f"磁盘选择: {disk_path}")
        self._show_disk_popup()
    
    def _show_disk_popup(self):
        """显示磁盘选择弹窗"""
        try:
            from ui.disk_selector.disk_popup import DiskPopupWidget
            from services.disk_info_provider import DiskInfoProvider
            
            if not hasattr(self, '_disk_popup') or self._disk_popup is None:
                self._disk_popup = DiskPopupWidget(self)
                self._disk_popup.disk_selected.connect(self._on_disk_popup_selected)
            
            if not hasattr(self, '_disk_provider') or self._disk_provider is None:
                self._disk_provider = DiskInfoProvider(self)
                self._disk_provider.disks_loaded.connect(self._on_disks_loaded)
                self._disk_provider.get_disk_info_async()
            else:
                self._popup_show()
        except Exception as e:
            logger.warning(f"磁盘选择弹窗不可用: {e}")
            self.path_changed.emit("")
    
    def _on_disks_loaded(self, disks):
        """磁盘信息加载完成"""
        if hasattr(self, '_disk_popup') and self._disk_popup:
            self._disk_popup.set_disks(disks)
            self._popup_show()
    
    def _popup_show(self):
        """显示弹窗"""
        if hasattr(self, '_disk_popup') and self._disk_popup:
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            global_pos.setY(global_pos.y() + 2)
            self._disk_popup.show_popup(global_pos)
    
    def _on_disk_popup_selected(self, disk_info):
        """磁盘弹窗选择完成"""
        if disk_info and hasattr(disk_info, 'path'):
            path = disk_info.path
        else:
            path = str(disk_info) if disk_info else ""
        
        if path:
            self._current_path = path
            self._breadcrumb.build_from_path(path)
            self.path_changed.emit(path)
            logger.info(f"磁盘选择完成，切换到: {path}")
    
    def _on_path_edit_return(self):
        """路径编辑回车事件"""
        new_path = self._path_edit.text().strip()
        
        if new_path and os.path.exists(new_path):
            self._current_path = new_path
            self.switch_to_breadcrumb_mode()
            self.path_changed.emit(new_path)
            logger.info(f"路径变更: {new_path}")
        else:
            # 路径无效，恢复原路径
            self._path_edit.setText(self._current_path)
            logger.warning(f"无效路径: {new_path}")
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self._path_edit:
            if event.type() == event.Type.KeyPress:
                key_event = QKeyEvent(event)
                if key_event.key() == Qt.Key_Escape:
                    # ESC键取消编辑
                    self.switch_to_breadcrumb_mode()
                    return True
            elif event.type() == event.Type.FocusOut:
                # 失去焦点时恢复面包屑模式
                self.switch_to_breadcrumb_mode()
                return True
        
        return super().eventFilter(obj, event)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.LeftButton:
            self.switch_to_edit_mode()
        super().mouseDoubleClickEvent(event)
    
    def apply_theme(self, theme_name: str):
        """
        应用主题
        
        Args:
            theme_name: 主题名称
        """
        self._breadcrumb.apply_theme(theme_name)
        
        if theme_name == "dark":
            style = """
                #win11AddressBar {
                    background-color: #2D2D2D;
                    border: none;
                }
                #pathEdit {
                    background-color: transparent;
                    border: none;
                    padding: 4px 8px;
                    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                    font-size: 9pt;
                    color: #FFFFFF;
                }
            """
        else:
            style = """
                #win11AddressBar {
                    background-color: #F8F8F8;
                    border: none;
                }
                #pathEdit {
                    background-color: transparent;
                    border: none;
                    padding: 4px 8px;
                    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                    font-size: 9pt;
                }
            """
        
        self.setStyleSheet(style)