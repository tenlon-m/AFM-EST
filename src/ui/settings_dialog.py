#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框模块
负责实现应用程序的设置界面
"""

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QPushButton, QFontComboBox, 
    QSpinBox, QGroupBox, QGridLayout, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from core.config import config_manager
from core.logger import logger

class SettingsDialog(QDialog):
    """
    设置对话框类
    实现应用程序的设置界面
    """
    
    # 定义设置更改信号
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        """
        初始化设置对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # 加载当前设置
        self.load_settings()
        
        # 初始化UI
        self.init_ui()
    
    def load_settings(self):
        """
        加载当前设置
        """
        # 加载文件列表字体设置
        self.folder_font = config_manager.get("ui.folder_font", "Microsoft YaHei")
        self.folder_font_size = config_manager.get("ui.folder_font_size", 10)
        self.file_font = config_manager.get("ui.file_font", "Microsoft YaHei")
        self.file_font_size = config_manager.get("ui.file_font_size", 10)
        # 加载功能设置
        self.remember_last_path = config_manager.get("ui.remember_last_path", True)
        self.auto_expand_to_current_folder = config_manager.get("ui.auto_expand_folder_tree", False)
        self.sync_panes = config_manager.get("ui.sync_panes", True)
    
    def save_settings(self):
        """
        保存设置
        """
        # 保存文件列表字体设置
        config_manager.set("ui.folder_font", self.folder_font)
        config_manager.set("ui.folder_font_size", self.folder_font_size)
        config_manager.set("ui.file_font", self.file_font)
        config_manager.set("ui.file_font_size", self.file_font_size)
        # 保存功能设置
        config_manager.set("ui.remember_last_path", self.remember_last_path)
        config_manager.set("ui.auto_expand_folder_tree", self.auto_expand_to_current_folder)
        config_manager.set("ui.sync_panes", self.sync_panes)
        
        # 保存配置到文件
        config_manager.save_config()
    
    def apply_settings(self):
        """
        应用设置
        """
        # 保存当前设置
        self.save_settings()
        
        # 发出设置已更改信号
        self.settings_changed.emit()
    
    def init_ui(self):
        """
        初始化UI组件
        """
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建外观设置标签页
        self.appearance_tab = QWidget()
        self.tab_widget.addTab(self.appearance_tab, "外观设置")
        self.setup_appearance_tab()
        
        # 创建功能设置标签页
        self.functionality_tab = QWidget()
        self.tab_widget.addTab(self.functionality_tab, "功能设置")
        self.setup_functionality_tab()
        
        # 创建预览配置标签页
        from ui.preview_config_tab import PreviewConfigTab
        self.preview_config_tab = PreviewConfigTab()
        self.tab_widget.addTab(self.preview_config_tab, "预览管理")
        self.preview_config_tab.config_changed.connect(self.on_preview_config_changed)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 确定按钮
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(self.ok_btn)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # 应用按钮
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self.on_apply_clicked)
        button_layout.addWidget(self.apply_btn)
        
        main_layout.addLayout(button_layout)
    
    def setup_appearance_tab(self):
        """
        设置外观设置标签页
        """
        # 创建主布局
        tab_layout = QVBoxLayout(self.appearance_tab)
        
        # 创建直接布局（取消分组外框）
        group_layout = QGridLayout()
        tab_layout.addLayout(group_layout)
        
        # 文件夹字体标签和选择框
        folder_font_label = QLabel("文件夹字体:")
        group_layout.addWidget(folder_font_label, 0, 0, Qt.AlignRight)
        
        self.folder_font_combo = QFontComboBox()
        self.folder_font_combo.setCurrentText(self.folder_font)
        self.folder_font_combo.currentTextChanged.connect(self.on_folder_font_changed)
        group_layout.addWidget(self.folder_font_combo, 0, 1)
        
        # 文件夹字号标签和选择框
        folder_font_size_label = QLabel("文件夹字号:")
        group_layout.addWidget(folder_font_size_label, 0, 2, Qt.AlignRight)
        
        self.folder_font_size_spin = QSpinBox()
        self.folder_font_size_spin.setRange(6, 24)
        self.folder_font_size_spin.setValue(self.folder_font_size)
        self.folder_font_size_spin.valueChanged.connect(self.on_folder_font_size_changed)
        group_layout.addWidget(self.folder_font_size_spin, 0, 3)
        
        # 文件名字体标签和选择框
        file_font_label = QLabel("文件名字体:")
        group_layout.addWidget(file_font_label, 1, 0, Qt.AlignRight)
        
        self.file_font_combo = QFontComboBox()
        self.file_font_combo.setCurrentText(self.file_font)
        self.file_font_combo.currentTextChanged.connect(self.on_file_font_changed)
        group_layout.addWidget(self.file_font_combo, 1, 1)
        
        # 文件名字号标签和选择框
        file_font_size_label = QLabel("文件名字号:")
        group_layout.addWidget(file_font_size_label, 1, 2, Qt.AlignRight)
        
        self.file_font_size_spin = QSpinBox()
        self.file_font_size_spin.setRange(6, 24)
        self.file_font_size_spin.setValue(self.file_font_size)
        self.file_font_size_spin.valueChanged.connect(self.on_file_font_size_changed)
        group_layout.addWidget(self.file_font_size_spin, 1, 3)
        
        # 占位符
        tab_layout.addStretch()
    
    def on_folder_font_changed(self, font_name):
        """
        文件夹字体更改事件
        
        Args:
            font_name: 新的字体名称
        """
        self.folder_font = font_name
    
    def on_folder_font_size_changed(self, font_size):
        """
        文件夹字号更改事件
        
        Args:
            font_size: 新的字号
        """
        self.folder_font_size = font_size
    
    def on_file_font_changed(self, font_name):
        """
        文件名字体更改事件
        
        Args:
            font_name: 新的字体名称
        """
        self.file_font = font_name
    
    def on_file_font_size_changed(self, font_size):
        """
        文件名字号更改事件
        
        Args:
            font_size: 新的字号
        """
        self.file_font_size = font_size
    
    def setup_functionality_tab(self):
        """
        设置功能设置标签页
        """
        # 创建主布局
        tab_layout = QVBoxLayout(self.functionality_tab)
        
        # 创建直接布局
        group_layout = QGridLayout()
        tab_layout.addLayout(group_layout)
        
        # 记住左右窗格最后浏览目录的复选框
        self.remember_path_check = QCheckBox("记住左右窗格最后浏览目录")
        self.remember_path_check.setChecked(self.remember_last_path)
        self.remember_path_check.stateChanged.connect(self.on_remember_path_changed)
        group_layout.addWidget(self.remember_path_check, 0, 0, 1, 4, Qt.AlignLeft)
        
        # 自动扩展到当前文件夹的复选框
        self.auto_expand_check = QCheckBox("点击磁盘选择按钮时自动扩展到当前文件夹")
        self.auto_expand_check.setChecked(self.auto_expand_to_current_folder)
        self.auto_expand_check.stateChanged.connect(self.on_auto_expand_changed)
        group_layout.addWidget(self.auto_expand_check, 1, 0, 1, 4, Qt.AlignLeft)
        
        # 左右窗格同步显示视图和分组的复选框
        self.sync_panes_check = QCheckBox("左右窗格同步显示视图切换和分组功能")
        self.sync_panes_check.setChecked(self.sync_panes)
        self.sync_panes_check.stateChanged.connect(self.on_sync_panes_changed)
        group_layout.addWidget(self.sync_panes_check, 2, 0, 1, 4, Qt.AlignLeft)
        
        # 占位符
        tab_layout.addStretch()
    
    def on_remember_path_changed(self, state):
        """
        记住路径设置更改事件
        
        Args:
            state: 复选框状态
        """
        self.remember_last_path = state == Qt.Checked
    
    def on_auto_expand_changed(self, state):
        """
        自动扩展到当前文件夹设置更改事件
        
        Args:
            state: 复选框状态
        """
        self.auto_expand_to_current_folder = state == Qt.Checked
    
    def on_sync_panes_changed(self, state):
        """
        左右窗格同步显示设置更改事件
        
        Args:
            state: 复选框状态
        """
        self.sync_panes = state == Qt.Checked
    
    def on_ok_clicked(self):
        """
        确定按钮点击事件
        """
        # 应用设置
        self.apply_settings()
        
        # 关闭对话框
        self.accept()
    
    def on_apply_clicked(self):
        """
        应用按钮点击事件
        """
        # 应用设置
        self.apply_settings()
    
    def on_preview_config_changed(self):
        """
        预览配置变更事件
        """
        # 发出设置已更改信号
        self.settings_changed.emit()
        logger.info("预览配置已变更")
