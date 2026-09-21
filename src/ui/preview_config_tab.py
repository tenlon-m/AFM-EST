#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览配置标签页
在设置对话框中管理预览文件类型配置
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QPushButton,
    QCheckBox, QSpinBox, QListWidget, QMessageBox,
    QFileDialog, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.preview_config_manager import preview_config_manager
from models.preview_config import HandlerConfig


class PreviewConfigTab(QWidget):
    """预览配置标签页"""
    
    # 配置变更信号
    config_changed = Signal()
    
    # 处理器名称中文映射
    HANDLER_NAME_MAP = {
        "MarkdownPreviewHandler": "Markdown文件",
        "CodeHighlightPreviewHandler": "代码文件",
        "TextPreviewHandler": "文本文件",
        "ImagePreviewHandler": "图片文件",
        "DocumentPreviewHandler": "文档文件",
        "AudioVideoPreviewHandler": "音视频文件",
        "ArchivePreviewHandler": "压缩文件",
        "SpecialFormatPreviewHandler": "特殊格式文件",
        "DefaultPreviewHandler": "默认处理器"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_handler: HandlerConfig = None
        self.init_ui()
        self.load_handlers()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：处理器表格
        left_panel = self._create_handler_table()
        splitter.addWidget(left_panel)
        
        # 右侧：详情面板
        right_panel = self._create_detail_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例（6:4）
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        
        main_layout.addWidget(splitter)
    
    def _create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 恢复默认按钮
        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.clicked.connect(self._on_reset_to_default)
        toolbar.addWidget(self.reset_btn)
        
        # 导出配置按钮
        self.export_btn = QPushButton("导出配置")
        self.export_btn.clicked.connect(self._on_export_config)
        toolbar.addWidget(self.export_btn)
        
        # 导入配置按钮
        self.import_btn = QPushButton("导入配置")
        self.import_btn.clicked.connect(self._on_import_config)
        toolbar.addWidget(self.import_btn)
        
        toolbar.addStretch()
        
        return toolbar
    
    def _create_handler_table(self) -> QWidget:
        """创建处理器表格"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title = QLabel("预览处理器列表")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 表格
        self.handler_table = QTableWidget()
        self.handler_table.setColumnCount(4)
        self.handler_table.setHorizontalHeaderLabels(["名称", "状态", "优先级", "扩展名数量"])
        
        # 设置表格属性
        self.handler_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.handler_table.setSelectionMode(QTableWidget.SingleSelection)
        self.handler_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.handler_table.verticalHeader().setVisible(False)
        
        # 设置列宽调整模式 - 允许用户手动调整
        header = self.handler_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # 允许用户拖动调整
        header.setStretchLastSection(False)  # 不自动拉伸最后一列
        
        # 设置默认列宽
        self.handler_table.setColumnWidth(0, 150)  # 名称列
        self.handler_table.setColumnWidth(1, 80)   # 状态列
        self.handler_table.setColumnWidth(2, 80)   # 优先级列
        self.handler_table.setColumnWidth(3, 100)  # 扩展名数量列
        
        # 启用滚动条
        self.handler_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.handler_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 连接选择信号
        self.handler_table.itemSelectionChanged.connect(self._on_handler_selected)
        
        layout.addWidget(self.handler_table)
        
        return widget
    
    def _create_detail_panel(self) -> QWidget:
        """创建详情面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        self.detail_title = QLabel("处理器详情")
        self.detail_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.detail_title)
        
        # 处理器名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("处理器名称:"))
        self.handler_name_label = QLabel("")
        self.handler_name_label.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(self.handler_name_label)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 启用状态
        enabled_layout = QHBoxLayout()
        enabled_layout.addWidget(QLabel("启用状态:"))
        self.enabled_checkbox = QCheckBox("启用")
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        enabled_layout.addWidget(self.enabled_checkbox)
        enabled_layout.addStretch()
        layout.addLayout(enabled_layout)
        
        # 优先级
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("优先级:"))
        self.priority_spinbox = QSpinBox()
        self.priority_spinbox.setRange(1, 100)
        self.priority_spinbox.valueChanged.connect(self._on_priority_changed)
        priority_layout.addWidget(self.priority_spinbox)
        priority_layout.addWidget(QLabel("(数值越小优先级越高)"))
        priority_layout.addStretch()
        layout.addLayout(priority_layout)
        
        # 扩展名列表
        extensions_label = QLabel("支持的扩展名:")
        extensions_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(extensions_label)
        
        # 扩展名列表控件（去掉边框）
        self.extensions_list = QListWidget()
        self.extensions_list.setSelectionMode(QListWidget.SingleSelection)
        self.extensions_list.setStyleSheet("QListWidget { border: 1px solid #ccc; }")
        layout.addWidget(self.extensions_list)
        
        # 扩展名操作按钮
        ext_btn_layout = QHBoxLayout()
        self.add_ext_btn = QPushButton("添加扩展名")
        self.add_ext_btn.clicked.connect(self._on_add_extension)
        ext_btn_layout.addWidget(self.add_ext_btn)
        
        self.remove_ext_btn = QPushButton("删除扩展名")
        self.remove_ext_btn.clicked.connect(self._on_remove_extension)
        ext_btn_layout.addWidget(self.remove_ext_btn)
        
        ext_btn_layout.addStretch()
        layout.addLayout(ext_btn_layout)
        
        return widget
    
    def load_handlers(self):
        """加载处理器列表"""
        handlers = preview_config_manager.get_handlers()
        
        self.handler_table.setRowCount(len(handlers))
        
        for i, handler in enumerate(handlers):
            # 名称（显示中文）
            chinese_name = self.HANDLER_NAME_MAP.get(handler.name, handler.name)
            name_item = QTableWidgetItem(chinese_name)
            name_item.setData(Qt.UserRole, handler.name)  # 保存原始名称
            self.handler_table.setItem(i, 0, name_item)
            
            # 状态
            status_item = QTableWidgetItem("启用" if handler.enabled else "禁用")
            status_item.setForeground(QColor("green") if handler.enabled else QColor("red"))
            self.handler_table.setItem(i, 1, status_item)
            
            # 优先级
            priority_item = QTableWidgetItem(str(handler.priority))
            self.handler_table.setItem(i, 2, priority_item)
            
            # 扩展名数量
            ext_count_item = QTableWidgetItem(str(len(handler.extensions)))
            self.handler_table.setItem(i, 3, ext_count_item)

    
    def _on_handler_selected(self):
        """处理器选择事件"""
        selected_rows = self.handler_table.selectedItems()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        # 从表格项中获取原始处理器名称
        name_item = self.handler_table.item(row, 0)
        handler_name = name_item.data(Qt.UserRole)  # 获取保存的原始名称
        
        # 获取处理器配置
        self._current_handler = preview_config_manager.get_handler(handler_name)
        
        if self._current_handler:
            self._update_detail_panel()
    
    def _update_detail_panel(self):
        """更新详情面板"""
        if not self._current_handler:
            return
        
        # 更新处理器名称（显示中文）
        chinese_name = self.HANDLER_NAME_MAP.get(
            self._current_handler.name, self._current_handler.name
        )
        self.handler_name_label.setText(chinese_name)
        
        # 更新启用状态
        self.enabled_checkbox.blockSignals(True)
        self.enabled_checkbox.setChecked(self._current_handler.enabled)
        self.enabled_checkbox.blockSignals(False)
        
        # 更新优先级
        self.priority_spinbox.blockSignals(True)
        self.priority_spinbox.setValue(self._current_handler.priority)
        self.priority_spinbox.blockSignals(False)
        
        # 更新扩展名列表
        self.extensions_list.clear()
        for ext in self._current_handler.extensions:
            self.extensions_list.addItem(ext)
    
    def _on_enabled_changed(self, state):
        """启用状态变更"""
        if not self._current_handler:
            return
        
        enabled = state == Qt.Checked
        result = preview_config_manager.set_handler_enabled(
            self._current_handler.name, enabled
        )
        
        if result.is_success:
            self._current_handler.enabled = enabled
            self.load_handlers()
            self.config_changed.emit()
        else:
            QMessageBox.warning(self, "操作失败", result.message)
            # 恢复状态
            self.enabled_checkbox.blockSignals(True)
            self.enabled_checkbox.setChecked(self._current_handler.enabled)
            self.enabled_checkbox.blockSignals(False)
    
    def _on_priority_changed(self, value):
        """优先级变更"""
        if not self._current_handler:
            return
        
        result = preview_config_manager.set_handler_priority(
            self._current_handler.name, value
        )
        
        if result.is_success:
            self._current_handler.priority = value
            self.load_handlers()
            self.config_changed.emit()
        else:
            QMessageBox.warning(self, "操作失败", result.message)
            # 恢复值
            self.priority_spinbox.blockSignals(True)
            self.priority_spinbox.setValue(self._current_handler.priority)
            self.priority_spinbox.blockSignals(False)
    
    def _on_add_extension(self):
        """添加扩展名"""
        if not self._current_handler:
            return
        
        # 弹出输入对话框
        from PySide6.QtWidgets import QInputDialog
        ext, ok = QInputDialog.getText(
            self, "添加扩展名", 
            "请输入扩展名（如 .txt 或 .tar.gz）:",
            text=".xxx"
        )
        
        if ok and ext:
            result = preview_config_manager.add_extension(
                self._current_handler.name, ext
            )
            
            if result.is_success:
                self._current_handler = preview_config_manager.get_handler(
                    self._current_handler.name
                )
                self._update_detail_panel()
                self.load_handlers()
                self.config_changed.emit()
            elif result.is_warning:
                QMessageBox.warning(self, "警告", result.message)
                self._current_handler = preview_config_manager.get_handler(
                    self._current_handler.name
                )
                self._update_detail_panel()
                self.load_handlers()
                self.config_changed.emit()
            else:
                QMessageBox.warning(self, "添加失败", result.message)
    
    def _on_remove_extension(self):
        """删除扩展名"""
        if not self._current_handler:
            return
        
        current_item = self.extensions_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的扩展名")
            return
        
        ext = current_item.text()
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除扩展名 {ext} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = preview_config_manager.remove_extension(
                self._current_handler.name, ext
            )
            
            if result.is_success:
                self._current_handler = preview_config_manager.get_handler(
                    self._current_handler.name
                )
                self._update_detail_panel()
                self.load_handlers()
                self.config_changed.emit()
            else:
                QMessageBox.warning(self, "删除失败", result.message)
    
    def _on_reset_to_default(self):
        """恢复默认配置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要恢复默认配置吗？当前配置将被覆盖。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = preview_config_manager.reset_to_default()
            
            if result.is_success:
                self.load_handlers()
                self._current_handler = None
                self._update_detail_panel()
                self.config_changed.emit()
                QMessageBox.information(self, "成功", "配置已恢复为默认值")
            else:
                QMessageBox.warning(self, "重置失败", result.message)
    
    def _on_export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出预览配置",
            "preview_config.yaml",
            "YAML文件 (*.yaml);;所有文件 (*)"
        )
        
        if file_path:
            result = preview_config_manager.export_config(file_path)
            
            if result.is_success:
                QMessageBox.information(self, "成功", result.message)
            else:
                QMessageBox.warning(self, "导出失败", result.message)
    
    def _on_import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入预览配置",
            "",
            "YAML文件 (*.yaml);;所有文件 (*)"
        )
        
        if file_path:
            reply = QMessageBox.question(
                self, "确认导入",
                "导入配置将覆盖当前配置，确定继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                result = preview_config_manager.import_config(file_path)
                
                if result.is_success:
                    self.load_handlers()
                    self._current_handler = None
                    self._update_detail_panel()
                    self.config_changed.emit()
                    QMessageBox.information(self, "成功", "配置导入成功")
                else:
                    QMessageBox.warning(self, "导入失败", result.message)