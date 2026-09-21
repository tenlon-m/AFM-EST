#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
磁盘空间分析对话框
显示磁盘空间占用情况的可视化界面
"""

import os
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QComboBox, QRadioButton, QGroupBox, QLineEdit, QSpinBox,
    QHeaderView, QMessageBox, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen
from PySide6.QtCore import QRect

def format_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

class DiskSpaceTreemap(QWidget):
    """
    磁盘空间树状图谱组件
    使用嵌套矩形显示空间占用比例，类似WinDirStat
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.setMinimumHeight(120)
    
    def set_data(self, items):
        """设置图表数据"""
        self.items = items[:50]
        for item in self.items:
            item['size_str'] = format_size(item['size'])
        self.update()
    
    def paintEvent(self, event):
        """绘制树状图谱"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        padding = 20
        chart_rect = rect.adjusted(padding, padding, -padding, -padding)
        
        if not self.items:
            painter.drawText(chart_rect, Qt.AlignCenter, "暂无数据")
            return
        
        total_size = sum(item['size'] for item in self.items)
        if total_size == 0:
            painter.drawText(chart_rect, Qt.AlignCenter, "暂无数据")
            return
        
        colors = [
            QColor(52, 152, 219), QColor(46, 204, 113),
            QColor(155, 89, 182), QColor(230, 126, 34),
            QColor(231, 76, 60), QColor(149, 165, 166),
            QColor(241, 196, 15), QColor(39, 174, 96),
            QColor(41, 128, 185), QColor(142, 68, 173),
            QColor(211, 84, 0), QColor(192, 57, 43),
            QColor(52, 73, 94), QColor(26, 188, 156),
            QColor(247, 220, 111), QColor(251, 140, 0),
            QColor(203, 67, 53), QColor(47, 54, 64)
        ]
        
        sorted_items = sorted(self.items, key=lambda x: x['size'], reverse=True)
        self._draw_treemap(painter, chart_rect, sorted_items, colors, 0, total_size)
        
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Microsoft YaHei", 9))
        
        legend_y = padding + 10
        for i, item in enumerate(sorted_items[:8]):
            color = colors[i % len(colors)]
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
            painter.drawRect(chart_rect.right() - 140, legend_y + i * 18, 12, 12)
            
            painter.setPen(QPen(Qt.black))
            name = item['name']
            if len(name) > 12:
                name = name[:9] + "..."
            painter.drawText(chart_rect.right() - 125, legend_y + i * 18 + 14, 120, 12, Qt.AlignVCenter, name)
    
    def _draw_treemap(self, painter, rect, items, colors, depth, total_size):
        """递归绘制树状图谱"""
        if not items or rect.width() < 10 or rect.height() < 10:
            return
        
        if len(items) == 1:
            item = items[0]
            color = colors[0 % len(colors)]
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 1))
            painter.drawRect(rect)
            
            if rect.width() > 80 and rect.height() > 40:
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
                
                name = item['name']
                if len(name) > 15:
                    name = name[:12] + "..."
                
                percent = (item['size'] / total_size) * 100
                text = f"{name}\n{format_size(item['size'])}\n{percent:.1f}%"
                painter.drawText(rect.adjusted(5, 5, -5, -5), Qt.AlignCenter, text)
            
            return
        
        is_vertical = rect.width() > rect.height()
        
        if is_vertical:
            current_x = rect.left()
            for i, item in enumerate(items):
                percent = item['size'] / total_size
                width = int(rect.width() * percent)
                
                if width < 5:
                    continue
                
                item_rect = QRect(current_x, rect.top(), width, rect.height())
                color = colors[i % len(colors)]
                
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(item_rect)
                
                if item_rect.width() > 60 and item_rect.height() > 30:
                    painter.setPen(QPen(Qt.white))
                    painter.setFont(QFont("Microsoft YaHei", 9))
                    
                    name = item['name']
                    if len(name) > 12:
                        name = name[:9] + "..."
                    
                    percent_text = (item['size'] / total_size) * 100
                    text = f"{name}\n{percent_text:.1f}%"
                    painter.drawText(item_rect.adjusted(5, 5, -5, -5), Qt.AlignCenter, text)
                
                current_x += width
        else:
            current_y = rect.top()
            for i, item in enumerate(items):
                percent = item['size'] / total_size
                height = int(rect.height() * percent)
                
                if height < 5:
                    continue
                
                item_rect = QRect(rect.left(), current_y, rect.width(), height)
                color = colors[i % len(colors)]
                
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(item_rect)
                
                if item_rect.width() > 60 and item_rect.height() > 30:
                    painter.setPen(QPen(Qt.white))
                    painter.setFont(QFont("Microsoft YaHei", 9))
                    
                    name = item['name']
                    if len(name) > 12:
                        name = name[:9] + "..."
                    
                    percent_text = (item['size'] / total_size) * 100
                    text = f"{name}\n{percent_text:.1f}%"
                    painter.drawText(item_rect.adjusted(5, 5, -5, -5), Qt.AlignCenter, text)
                
                current_y += height

class DiskSpaceBarChart(QWidget):
    """
    磁盘空间条形图组件
    显示空间占用的可视化图谱
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.max_size = 0
        self.setMinimumHeight(120)
    
    def set_data(self, items):
        """设置图表数据"""
        self.items = items[:20]
        for item in self.items:
            item['size_str'] = format_size(item['size'])
        
        if self.items:
            self.max_size = max(item['size'] for item in self.items)
        else:
            self.max_size = 0
        
        self.update()
    
    def paintEvent(self, event):
        """绘制图表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        padding = 20
        chart_rect = rect.adjusted(padding, padding, -padding, -padding)
        
        if not self.items or self.max_size == 0:
            painter.drawText(chart_rect, Qt.AlignCenter, "暂无数据")
            return
        
        item_height = 25
        spacing = 5
        total_height = len(self.items) * (item_height + spacing)
        
        colors = [
            QColor(52, 152, 219), QColor(46, 204, 113),
            QColor(155, 89, 182), QColor(230, 126, 34),
            QColor(231, 76, 60), QColor(149, 165, 166),
            QColor(241, 196, 15), QColor(236, 240, 241),
            QColor(127, 140, 141), QColor(39, 174, 96),
            QColor(41, 128, 185), QColor(142, 68, 173),
            QColor(211, 84, 0), QColor(192, 57, 43),
            QColor(52, 73, 94), QColor(26, 188, 156),
            QColor(247, 220, 111), QColor(251, 140, 0),
            QColor(203, 67, 53), QColor(47, 54, 64)
        ]
        
        start_y = 0
        
        for i, item in enumerate(self.items):
            y = start_y + i * (item_height + spacing)
            
            if y + item_height > chart_rect.height():
                break
            
            percent = (item['size'] / self.max_size) * 100
            bar_width = (chart_rect.width() - 150) * (percent / 100)
            
            color = colors[i % len(colors)]
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
            
            bar_rect = QRect(chart_rect.left() + 145, y, bar_width, item_height)
            painter.drawRect(bar_rect)
            
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Microsoft YaHei", 9))
            
            name = item['name']
            if len(name) > 30:
                name = name[:27] + "..."
            
            painter.drawText(chart_rect.left(), y, 140, item_height, Qt.AlignVCenter | Qt.AlignRight, name)
            
            size_str = item.get('size_str', format_size(item['size']))
            painter.drawText(chart_rect.left() + 145 + bar_width + 5, y, 100, item_height, Qt.AlignVCenter, size_str)

class DiskSpaceDialog(QDialog):
    """
    磁盘空间分析对话框类
    """
    
    analysis_finished = Signal(list, dict)
    progress_updated = Signal(int, int, str)
    status_updated = Signal(str)
    total_size_updated = Signal(str)
    
    def __init__(self, current_path: str = "", parent=None):
        """
        初始化对话框
        
        Args:
            current_path: 当前路径
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("磁盘空间分析")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        
        self.current_path = current_path
        self.drive_path = self._get_drive_path(current_path)
        
        self.disk_space_service = None
        self.analysis_thread = None
        self.stop_event = threading.Event()
        self.results = []
        
        self.init_ui()
        self._connect_signals()
    
    def _connect_signals(self):
        """连接信号"""
        self.analysis_finished.connect(self._on_analysis_finished)
        self.progress_updated.connect(self._on_progress_updated)
        self.status_updated.connect(self._on_status_updated)
        self.total_size_updated.connect(self._on_total_size_updated)
    
    def _get_drive_path(self, path: str) -> str:
        """
        从路径中提取驱动器路径
        
        Args:
            path: 文件路径
            
        Returns:
            驱动器路径（如 "C:\\"）
        """
        if not path:
            return ""
        
        drive, _ = os.path.splitdrive(path)
        if drive:
            return f"{drive}\\"
        
        return ""
    
    def _populate_drives(self):
        """填充驱动器列表"""
        if os.name == 'nt':
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive = f"{chr(ord('A') + i)}:\\"
                    try:
                        if os.path.isdir(drive):
                            self.path_combo.addItem(drive)
                    except Exception:
                        pass
        else:
            self.path_combo.addItem("/")
    
    def init_ui(self):
        """初始化UI组件"""
        from services.disk_space_service import DiskSpaceService
        self.disk_space_service = DiskSpaceService()
        
        main_layout = QVBoxLayout(self)
        
        control_group = QGroupBox("分析选项")
        control_layout = QVBoxLayout(control_group)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("分析类型:"))
        
        self.radio_disk = QRadioButton("磁盘文件夹")
        self.radio_disk.setChecked(True)
        self.radio_folder = QRadioButton("指定文件夹")
        self.radio_large = QRadioButton("大文件")
        
        type_layout.addWidget(self.radio_disk)
        type_layout.addWidget(self.radio_folder)
        type_layout.addWidget(self.radio_large)
        type_layout.addStretch()
        control_layout.addLayout(type_layout)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("路径:"))
        
        self.path_combo = QComboBox()
        self.path_combo.setMinimumWidth(300)
        self._populate_drives()
        
        if self.drive_path:
            index = self.path_combo.findText(self.drive_path)
            if index >= 0:
                self.path_combo.setCurrentIndex(index)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("输入文件夹路径")
        self.path_edit.setEnabled(False)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setEnabled(False)
        self.browse_btn.clicked.connect(self._browse_folder)
        
        path_layout.addWidget(self.path_combo)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        control_layout.addLayout(path_layout)
        
        large_layout = QHBoxLayout()
        large_layout.addWidget(QLabel("大文件阈值:"))
        
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(1, 10240)
        self.min_size_spin.setValue(100)
        self.min_size_spin.setSuffix(" MB")
        self.min_size_spin.setEnabled(False)
        
        large_layout.addWidget(self.min_size_spin)
        large_layout.addStretch()
        control_layout.addLayout(large_layout)
        
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("排序方式:"))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["按大小降序", "按大小升序", "按名称", "按类型"])
        sort_layout.addWidget(self.sort_combo)
        
        self.refresh_btn = QPushButton("重新分析")
        self.refresh_btn.clicked.connect(self._start_analysis)
        sort_layout.addWidget(self.refresh_btn)
        
        control_layout.addLayout(sort_layout)
        
        main_layout.addWidget(control_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        main_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        main_layout.addWidget(self.progress_label)
        
        disk_info_group = QGroupBox("磁盘使用情况")
        disk_info_layout = QHBoxLayout(disk_info_group)
        
        self.disk_total_label = QLabel("总容量: --")
        self.disk_used_label = QLabel("已使用: --")
        self.disk_free_label = QLabel("可用: --")
        self.disk_percent_label = QLabel("使用率: --")
        
        disk_info_layout.addWidget(self.disk_total_label)
        disk_info_layout.addWidget(self.disk_used_label)
        disk_info_layout.addWidget(self.disk_free_label)
        disk_info_layout.addWidget(self.disk_percent_label)
        disk_info_layout.addStretch()
        
        main_layout.addWidget(disk_info_group)
        
        tab_widget = QTabWidget()
        
        treemap_container = QWidget()
        treemap_layout = QVBoxLayout(treemap_container)
        treemap_layout.setContentsMargins(0, 0, 0, 0)
        self.treemap_widget = DiskSpaceTreemap()
        treemap_layout.addWidget(self.treemap_widget)
        tab_widget.addTab(treemap_container, "树状图谱")
        
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_widget = DiskSpaceBarChart()
        chart_layout.addWidget(self.chart_widget)
        tab_widget.addTab(chart_container, "条形图谱")
        
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["名称", "路径", "大小", "类型"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(tab_widget)
        splitter.addWidget(self.table_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([350, 350])
        
        main_layout.addWidget(splitter)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.total_size_label = QLabel("总计: --")
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.total_size_label)
        
        main_layout.addLayout(status_layout)
        
        self.radio_disk.toggled.connect(self._on_type_changed)
        self.radio_folder.toggled.connect(self._on_type_changed)
        self.radio_large.toggled.connect(self._on_type_changed)
        self.path_combo.currentTextChanged.connect(self._on_path_changed)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        
        self._start_analysis()
    
    def _on_type_changed(self):
        """分析类型改变处理"""
        if self.radio_disk.isChecked():
            self.path_combo.setEnabled(True)
            self.path_edit.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.min_size_spin.setEnabled(False)
        elif self.radio_folder.isChecked():
            self.path_combo.setEnabled(False)
            self.path_edit.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.min_size_spin.setEnabled(False)
        elif self.radio_large.isChecked():
            self.path_combo.setEnabled(True)
            self.path_edit.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.min_size_spin.setEnabled(True)
    
    def _on_path_changed(self, path):
        """路径改变处理"""
        self.drive_path = path
        self._update_disk_info()
    
    def _on_sort_changed(self):
        """排序方式改变处理"""
        self._sort_results()
    
    def _browse_folder(self):
        """浏览文件夹"""
        from PySide6.QtWidgets import QFileDialog
        
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", self.current_path)
        if folder:
            self.path_edit.setText(folder)
            self._start_analysis()
    
    def _update_disk_info(self):
        """更新磁盘使用信息"""
        drive_path = self.path_combo.currentText() if self.radio_disk.isChecked() or self.radio_large.isChecked() else self.path_edit.text()
        
        if drive_path:
            usage = self.disk_space_service.get_disk_usage(drive_path)
            
            self.disk_total_label.setText(f"总容量: {format_size(usage['total'])}")
            self.disk_used_label.setText(f"已使用: {format_size(usage['used'])}")
            self.disk_free_label.setText(f"可用: {format_size(usage['free'])}")
            self.disk_percent_label.setText(f"使用率: {usage['percent_used']:.1f}%")
    
    def _start_analysis(self):
        """开始分析"""
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.stop_event.set()
            self.analysis_thread.join(timeout=5)
        
        self.stop_event.clear()
        
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.table_widget.setRowCount(0)
        self.chart_widget.set_data([])
        self.treemap_widget.set_data([])
        self.status_label.setText("分析中...")
        self.total_size_label.setText("总计: --")
        
        drive_path = self.path_combo.currentText() if self.radio_disk.isChecked() or self.radio_large.isChecked() else self.path_edit.text()
        
        if not drive_path:
            QMessageBox.warning(self, "警告", "请选择或输入路径")
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.status_label.setText("就绪")
            return
        
        if not os.path.exists(drive_path):
            QMessageBox.warning(self, "警告", "路径不存在")
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.status_label.setText("就绪")
            return
        
        self.analysis_thread = threading.Thread(
            target=self._analyze,
            args=(drive_path,),
            daemon=True
        )
        self.analysis_thread.start()
    
    def _analyze(self, path):
        """执行分析（后台线程）"""
        self.disk_space_service.reset()
        
        def progress_callback(current, total, message):
            self.progress_updated.emit(current, total, message)
        
        self.disk_space_service.set_progress_callback(progress_callback)
        
        try:
            if self.radio_disk.isChecked():
                results = self.disk_space_service.analyze_disk_folders(path)
            elif self.radio_folder.isChecked():
                results = self.disk_space_service.analyze_specific_folder(path)
            elif self.radio_large.isChecked():
                min_size = self.min_size_spin.value()
                results = self.disk_space_service.analyze_large_files(path, min_size)
            
            if self.stop_event.is_set():
                return
            
            drive_path = self.path_combo.currentText() if self.radio_disk.isChecked() or self.radio_large.isChecked() else self.path_edit.text()
            usage = self.disk_space_service.get_disk_usage(drive_path)
            
            self.analysis_finished.emit(results, usage)
            
        except Exception as e:
            self.status_updated.emit(f"分析失败: {str(e)}")
    
    def _on_analysis_finished(self, results, usage):
        """分析完成回调（主线程）"""
        self.results = results
        self._update_disk_info_with_usage(usage)
        self._sort_results()
        self._populate_table()
        self.chart_widget.set_data(self.results)
        self.treemap_widget.set_data(self.results)
        
        total_size = sum(item['size'] for item in results)
        self.total_size_updated.emit(f"总计: {format_size(total_size)}")
        self.status_updated.emit(f"分析完成，共 {len(results)} 个项目")
        
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
    
    def _update_disk_info_with_usage(self, usage):
        """使用提供的usage数据更新磁盘信息"""
        self.disk_total_label.setText(f"总容量: {format_size(usage['total'])}")
        self.disk_used_label.setText(f"已使用: {format_size(usage['used'])}")
        self.disk_free_label.setText(f"可用: {format_size(usage['free'])}")
        self.disk_percent_label.setText(f"使用率: {usage['percent_used']:.1f}%")
    
    def _on_progress_updated(self, current, total, message):
        """进度更新回调（主线程）"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def _on_status_updated(self, message):
        """状态更新回调（主线程）"""
        self.status_label.setText(message)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
    
    def _on_total_size_updated(self, message):
        """总大小更新回调（主线程）"""
        self.total_size_label.setText(message)
    
    def _sort_results(self):
        """排序结果"""
        if not self.results:
            return
        
        sort_by = 'size'
        ascending = False
        
        current_text = self.sort_combo.currentText()
        if current_text == "按大小升序":
            ascending = True
        elif current_text == "按名称":
            sort_by = 'name'
            ascending = False
        elif current_text == "按类型":
            sort_by = 'type'
            ascending = False
        
        self.results = self.disk_space_service.sort_results(self.results, sort_by, ascending)
        self._populate_table()
        self.chart_widget.set_data(self.results)
        self.treemap_widget.set_data(self.results)
    
    def _populate_table(self):
        """填充表格"""
        self.table_widget.setRowCount(len(self.results))
        
        for row, item in enumerate(self.results):
            name_item = QTableWidgetItem(item['name'])
            path_item = QTableWidgetItem(item['path'])
            size_item = QTableWidgetItem(format_size(item['size']))
            type_item = QTableWidgetItem("文件夹" if item['type'] == 'folder' else "文件")
            
            name_item.setData(Qt.UserRole, item['size'])
            size_item.setTextAlignment(Qt.AlignRight)
            
            self.table_widget.setItem(row, 0, name_item)
            self.table_widget.setItem(row, 1, path_item)
            self.table_widget.setItem(row, 2, size_item)
            self.table_widget.setItem(row, 3, type_item)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_event.set()
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        event.accept()