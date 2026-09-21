#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能面板模块
包含搜索、预览、对比和传输等功能面板
"""

# pyright: reportOptionalMemberAccess=false, reportUnannotatedClassAttribute=false

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QGridLayout, QLineEdit, QPushButton,
    QCheckBox, QComboBox,
    QDialog, QTableView, QHBoxLayout, QHeaderView, QTabWidget, QProgressBar,
    QMenu, QGraphicsView, QGroupBox, QTextEdit, QFormLayout,
    QFrame, QTableWidgetItem, QFileDialog, QMessageBox, QApplication
)
from core.utils import show_warning, show_info, detect_file_encoding, format_size
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem

import os

# 使用新的统一搜索服务（NTFS快速搜索 + Whoosh全文搜索）
from services.unified_search_service import unified_search_service
from services.preview_service import preview_service
from services.file_diff_service import file_diff_service
from services.ftp_service import ftp_service
from services.p2p.p2p_service import P2PService
p2p_service = P2PService()
from services.tools_service import tools_service
from core.logger import logger
from core.config import config_manager

class FunctionPanel(QTabWidget):
    """
    功能面板类
    包含搜索、预览、对比和传输等功能面板
    """
    
    def __init__(self, parent: QWidget | None = None):
        """
        初始化功能面板
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._parent = parent
        self.config = config_manager  # 添加配置管理器属性
        
        # 搜索状态变量
        self.search_runnable = None  # 当前搜索任务
        
        # 初始化快速搜索索引（后台异步构建）
        self._init_fast_search_index()
        self.search_paused = False   # 搜索是否暂停
        self.search_stopped = False  # 搜索是否停止
        
        # 预览相关变量
        self.preview_file_info = None
        self.current_preview_file = None
        self.default_preview_label = None
        self.preview_content = None
        self.preview_content_layout = None
        
        # 搜索相关变量
        self.search_keyword = None
        self.search_directory = None
        self.include_subdirectories = None
        self.search_content = None
        self.file_type_combo = None
        self.current_file_label = None
        self.searched_count_label = None
        self.total_files_label = None
        self.success_count_label = None
        self.progress_label = None
        self.progress_bar = None
        self.pause_btn = None
        self.stop_btn = None
        
        # 文件对比面板变量
        self.file1_edit = None
        self.file2_edit = None
        self.ignore_whitespace = None
        self.ignore_case = None
        self.current_diff_result = None
        
        # FTP客户端面板变量
        self.host_edit = None
        self.port_edit = None
        self.protocol_combo = None
        self.username_edit = None
        self.password_edit = None
        self.operation_combo = None
        self.local_path_edit = None
        self.remote_path_edit = None
        self.task_table = None
        self.refresh_tasks_btn = None
        self.clear_tasks_btn = None
        self.current_connection = None
        self.connection_id = None
        self.task_timer = None
        
        # P2P传输面板变量
        self.start_p2p_btn = None
        self.stop_p2p_btn = None
        self.scan_btn = None
        self.device_list = None
        self.connection_status_label = None
        self.connection_info_label = None
        self.connect_btn = None
        self.disconnect_btn = None
        self.history_btn = None
        self.current_connection_label = None
        self.send_file_btn = None
        self.receive_settings_btn = None
        self.p2p_task_table = None
        self.task_detail_group = None
        self.task_detail_info = None
        self.p2p_pause_btn = None
        self.p2p_resume_btn = None
        self.p2p_cancel_btn = None
        self.hide_detail_btn = None
        self.current_p2p_file = None
        self.current_p2p_files = None
        self.current_p2p_task_id = None
        self.connection_status = None
        self.p2p_current_connection = None
        self.transfer_request_dialog = None
        self.selected_device = None
        self.device_scan_timer = None
        self.task_refresh_timer = None
        
        # 辅助工具面板变量（在 _setup_tools_panel 中初始化）
        self.tools_tab_widget = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_type_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.prefix_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.suffix_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.old_text_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.new_text_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.start_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.padding_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_preview = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.target_encoding_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.backup_checkbox = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_preview = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.target_format_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.quality_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.overwrite_checkbox = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_info_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.hash_algo_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_result_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_output_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_insert_title_check = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_insert_blank_check = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_preview_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.current_task = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.save_path_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        
        self.init_ui()
        
        # 设置支持拖拽
        self.setAcceptDrops(True)
    
    def init_ui(self):
        """
        初始化功能面板UI组件
        """
        # 设置标签位置和样式
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setMinimumWidth(250)
        self.setMinimumHeight(400)
        self.setTabShape(QTabWidget.TabShape.Rounded)  # type: ignore[reportAttributeAccessIssue]
        
        # 创建搜索面板
        self.search_tab = QWidget()
        self._setup_search_panel()
        self.addTab(self.search_tab, "搜索")
        
        # 创建对比面板
        self.compare_tab = QWidget()
        self._setup_compare_panel()
        self.addTab(self.compare_tab, "对比")
        
        # 创建预览面板
        self.preview_tab = QWidget()
        self._setup_preview_panel()
        self.addTab(self.preview_tab, "预览")
        
        # 创建传输面板
        self.transfer_tab = QWidget()
        self._setup_transfer_panel()
        self.addTab(self.transfer_tab, "Ftp")
        
        # 创建P2P传输面板
        self.p2p_tab = QWidget()
        self._setup_p2p_panel()
        self.addTab(self.p2p_tab, "P2P")
        
        # 创建辅助工具面板
        self.tools_tab = QWidget()
        self._setup_tools_panel()
        self.addTab(self.tools_tab, "辅助")
    
    def _setup_preview_panel(self):
        """
        设置预览面板的UI组件和布局
        """
        # 创建预览面板布局
        preview_layout = QVBoxLayout(self.preview_tab)
        
        # 添加文件信息标签，显示文件路径和文件名
        self.preview_file_info = QLabel()
        self.preview_file_info.setStyleSheet("""QLabel {
            background-color: #f0f0f0;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }""")
        self.preview_file_info.setWordWrap(True)
        self.preview_file_info.setVisible(False)
        preview_layout.addWidget(self.preview_file_info)
        
        # 创建预览区域
        self.preview_content = QWidget()
        # 为预览内容区域添加双击事件处理
        self.preview_content.mouseDoubleClickEvent = self._on_preview_double_click
        self.preview_content_layout = QVBoxLayout(self.preview_content)
        self.preview_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 添加默认提示
        self.default_preview_label = QLabel("选择文件以预览")
        self.default_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.default_preview_label.setStyleSheet("font-size: 16px; color: #888;")
        self.preview_content_layout.addWidget(self.default_preview_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.preview_content)
        scroll_area.setWidgetResizable(True)
        # 移除滚动区域的边框，避免与内部组件边框重叠
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # 添加到预览面板布局
        preview_layout.addWidget(scroll_area)
    
    def _setup_search_panel(self):
        """
        设置搜索面板的UI组件和布局
        """
        # 创建搜索面板布局
        search_layout = QVBoxLayout(self.search_tab)
        
        # 创建搜索条件区域
        criteria_layout = QGridLayout()
        
        # 搜索关键字
        criteria_layout.addWidget(QLabel("关键字:"), 0, 0)
        self.search_keyword = QComboBox()
        self.search_keyword.setEditable(True)
        self.search_keyword.setPlaceholderText("输入搜索关键字")
        # 设置大小调整策略和最小宽度
        self.search_keyword.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.search_keyword.setMinimumWidth(150)
        # 移除自定义样式，使用系统默认样式，确保下拉箭头正确显示
        criteria_layout.addWidget(self.search_keyword, 0, 1, 1, 3)
        
        # 搜索目录
        criteria_layout.addWidget(QLabel("搜索目录:"), 1, 0)
        self.search_directory = QComboBox()
        self.search_directory.setEditable(True)
        self.search_directory.setPlaceholderText("选择搜索目录")
        # 设置大小调整策略和最小宽度
        self.search_directory.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.search_directory.setMinimumWidth(150)
        # 移除自定义样式，使用系统默认样式，确保下拉箭头正确显示
        criteria_layout.addWidget(self.search_directory, 1, 1, 1, 2)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_search_directory)
        criteria_layout.addWidget(browse_btn, 1, 3)
        
        # 包含子目录
        self.include_subdirectories = QCheckBox("包含子目录")
        self.include_subdirectories.setChecked(True)
        criteria_layout.addWidget(self.include_subdirectories, 2, 0, 1, 2)
        
        # 搜索文件内容
        self.search_content = QCheckBox("搜索文件内容")
        self.search_content.setChecked(False)
        criteria_layout.addWidget(self.search_content, 2, 2, 1, 2)
        
        # 文件类型
        criteria_layout.addWidget(QLabel("文件类型:"), 3, 0)
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItem("所有文件")
        self.file_type_combo.addItem("文本文件")
        self.file_type_combo.addItem("图片文件")
        self.file_type_combo.addItem("文档文件")
        self.file_type_combo.addItem("压缩文件")
        self.file_type_combo.addItem("音频文件")
        self.file_type_combo.addItem("视频文件")
        criteria_layout.addWidget(self.file_type_combo, 3, 1, 1, 3)
        
        # 搜索按钮
        search_btn = QPushButton("开始搜索")
        search_btn.clicked.connect(self._start_search)
        # 设置按钮固定大小
        search_btn.setFixedSize(80, 30)
        criteria_layout.addWidget(search_btn, 4, 0)
        
        # 暂停搜索按钮
        self.pause_btn = QPushButton("暂停搜索")
        self.pause_btn.clicked.connect(self._pause_search)
        self.pause_btn.setEnabled(False)  # 初始禁用
        # 设置按钮固定大小
        self.pause_btn.setFixedSize(80, 30)
        criteria_layout.addWidget(self.pause_btn, 4, 1)
        
        # 停止搜索按钮
        self.stop_btn = QPushButton("停止搜索")
        self.stop_btn.clicked.connect(self._stop_search)
        self.stop_btn.setEnabled(False)  # 初始禁用
        # 设置按钮固定大小
        self.stop_btn.setFixedSize(80, 30)
        criteria_layout.addWidget(self.stop_btn, 4, 2)
        
        # 创建容器部件并设置布局
        criteria_container = QWidget()
        criteria_container.setLayout(criteria_layout)
        
        # 添加搜索条件区域到搜索面板
        search_layout.addWidget(criteria_container)
        
        # 添加搜索进度显示区域
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)  # 使用垂直布局
        
        # 当前搜索文件名
        self.current_file_label = QLabel("准备搜索...")
        self.current_file_label.setMinimumWidth(100)
        progress_layout.addWidget(self.current_file_label)
        
        # 搜索统计信息
        stats_layout = QVBoxLayout()  # 使用垂直布局替代水平布局
        
        # 已搜索文件数
        self.searched_count_label = QLabel("已搜索: 0")
        stats_layout.addWidget(self.searched_count_label)
        
        # 总文件数
        self.total_files_label = QLabel("总文件: 0")
        stats_layout.addWidget(self.total_files_label)
        
        # 搜索成功文件数
        self.success_count_label = QLabel("已找到: 0")
        stats_layout.addWidget(self.success_count_label)
        
        stats_container = QWidget()
        stats_container.setLayout(stats_layout)
        progress_layout.addWidget(stats_container)
        
        self.progress_label = QLabel("准备搜索...")
        self.progress_label.setMinimumWidth(100)
        self.progress_label.setVisible(False)  # 隐藏旧标签，使用新标签
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始隐藏
        progress_layout.addWidget(self.progress_bar)
        
        search_layout.addWidget(progress_container)
        
        # 添加伸缩项，将搜索控件推到顶部
        search_layout.addStretch()
        
        # 加载搜索历史
        self._load_search_history()
    
    def _init_fast_search_index(self):
        """
        初始化快速搜索索引
        
        索引检查已移到 AFM-EST.py 的启动流程中，
        在启动画面关闭后才会触发 _check_and_prompt_index
        """
        pass
    
    def _check_and_prompt_index(self):
        try:
            fast_search_built = unified_search_service.fast_search.index_built
            fulltext_search_built = unified_search_service.fulltext_search.index_built
            whoosh_indexing = unified_search_service.fulltext_search.is_indexing
            
            if fast_search_built and fulltext_search_built:
                logger.info("快速搜索和全文索引均已存在，无需构建")
                return
            
            if fast_search_built and not fulltext_search_built and not whoosh_indexing:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "全文索引",
                    "快速搜索索引已存在，但全文索引尚未构建。\n\n"
                    "全文索引将在后台构建，不影响正常使用。\n"
                    "（构建后内容搜索速度提升100-1000倍）\n\n"
                    "是否现在构建全文索引？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._start_whoosh_background()
                return
            
            if whoosh_indexing:
                logger.info("全文索引正在后台构建中")
                return
            
            missing_indexes = []
            if not fast_search_built:
                missing_indexes.append("快速搜索索引")
            if not fulltext_search_built:
                missing_indexes.append("全文索引")
            
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "搜索索引",
                f"检测到以下搜索索引尚未构建：{', '.join(missing_indexes)}。\n\n"
                "首次使用需要构建索引（将自动检测所有可用磁盘），\n"
                "构建后搜索速度将提升100-1000倍！\n\n"
                "是否现在开始构建？\n"
                "（也可以稍后在搜索时自动构建）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._build_search_index_with_progress()
            else:
                logger.info("用户选择稍后构建索引")
        
        except Exception as e:
            logger.error(f"[UI] 初始化搜索索引失败: {e}")
    
    def _build_search_index_with_progress(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
        from PySide6.QtCore import QTimer, Qt, QObject, Signal
        import threading
        
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("构建快速搜索索引")
        progress_dialog.setMinimumSize(520, 180)
        progress_dialog.setModal(False)
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(progress_dialog)
        layout.setSpacing(6)
        
        title_label = QLabel("正在构建 NTFS 文件名索引...")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        info_label = QLabel(
            "NTFS 索引完成后即可使用文件名快速搜索。\n"
            "全文索引将在后台继续构建，进度显示在状态栏。"
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)
        
        ntfs_progress_bar = QProgressBar()
        ntfs_progress_bar.setRange(0, 100)
        ntfs_progress_bar.setValue(0)
        ntfs_progress_bar.setFixedHeight(20)
        ntfs_progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #ccc; border-radius: 4px; background: #f0f0f0; text-align: center; font-size: 10px; }
            QProgressBar::chunk { background: #4CAF50; border-radius: 3px; }
        """)
        layout.addWidget(ntfs_progress_bar)
        
        ntfs_status_label = QLabel("等待开始...")
        ntfs_status_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(ntfs_status_label)
        
        QTimer.singleShot(500, lambda: progress_dialog.show())
        
        class ProgressSignals(QObject):
            update_ntfs_progress = Signal(int)
            update_ntfs_status = Signal(str)
            ntfs_complete = Signal()
            build_error = Signal(str)
        
        signals = ProgressSignals()
        signals.update_ntfs_progress.connect(ntfs_progress_bar.setValue)
        signals.update_ntfs_status.connect(ntfs_status_label.setText)
        
        def on_ntfs_complete():
            ntfs_progress_bar.setValue(100)
            progress_dialog.accept()
            self._start_whoosh_background()
        
        def on_build_error(err):
            progress_dialog.reject()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "索引构建失败",
                f"索引构建失败:\n{err}\n\n将使用传统搜索方式（较慢）"
            )
        
        signals.ntfs_complete.connect(on_ntfs_complete)
        signals.build_error.connect(on_build_error)
        
        def progress_callback_safe(*args):
            try:
                progress_type = args[0] if args else None

                if progress_type == "ntfs" and len(args) == 5:
                    _, drive, progress, processed, total = args
                    progress_val = max(1, min(round(progress), 100)) if progress > 0 else 0
                    status_text = f"[{drive}]: {progress:.1f}% ({processed}/{total} 文件)"
                    signals.update_ntfs_progress.emit(progress_val)
                    signals.update_ntfs_status.emit(status_text)
            except Exception as e:
                logger.error(f"进度回调错误: {e}")
        
        def build_ntfs_in_background():
            try:
                from services.unified_search_service import unified_search_service
                drives = unified_search_service._detect_indexable_drives()
                
                def ntfs_callback(drive, progress, indexed, total):
                    progress_callback_safe("ntfs", drive, progress, indexed, total)
                
                unified_search_service.fast_search.build_index_async(drives, ntfs_callback)
                unified_search_service.fast_search.build_event.wait()
                unified_search_service.fast_search.index_built = True
                
                signals.ntfs_complete.emit()
            except Exception as e:
                logger.error(f"NTFS索引构建失败: {e}")
                signals.build_error.emit(str(e))
        
        thread = threading.Thread(target=build_ntfs_in_background, daemon=True)
        thread.start()
    
    def _start_whoosh_background(self):
        from PySide6.QtCore import QObject, Signal
        import threading
        from services.unified_search_service import unified_search_service
        
        class WhooshSignals(QObject):
            update_status = Signal(str)
            update_progress = Signal(int)
            whoosh_complete = Signal()
            whoosh_error = Signal(str)
        
        whoosh_signals = WhooshSignals()
        
        main_window = self.window()
        
        def on_whoosh_status(status_text):
            if main_window and hasattr(main_window, 'whoosh_index_status'):
                main_window.whoosh_index_status.setText(status_text)  # pyright: ignore[reportAttributeAccessIssue]
        
        def on_whoosh_progress(val):
            if main_window and hasattr(main_window, 'whoosh_index_progress'):
                main_window.whoosh_index_progress.setValue(val)  # pyright: ignore[reportAttributeAccessIssue]
        
        def on_whoosh_complete():
            if main_window and hasattr(main_window, 'whoosh_index_status'):
                main_window.whoosh_index_status.setText("全文索引: 已完成")  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setValue(100)  # pyright: ignore[reportAttributeAccessIssue]
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "全文索引构建完成",
                "Whoosh 全文索引构建成功！\n\n"
                "现在可以使用文件内容搜索功能了！\n"
                "（搜索速度提升100-1000倍）"
            )
            if main_window and hasattr(main_window, 'whoosh_index_status'):
                main_window.whoosh_index_status.setText("")  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.hide()  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_status.hide()  # pyright: ignore[reportAttributeAccessIssue]
        
        whoosh_signals.update_status.connect(on_whoosh_status)
        whoosh_signals.update_progress.connect(on_whoosh_progress)
        whoosh_signals.whoosh_complete.connect(on_whoosh_complete)
        
        if main_window:
            if not hasattr(main_window, 'whoosh_index_status'):
                from PySide6.QtWidgets import QLabel, QProgressBar
                main_window.whoosh_index_progress = QProgressBar()  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setRange(0, 100)  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setValue(0)  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setFixedWidth(120)  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setFixedHeight(14)  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setStyleSheet(  # pyright: ignore[reportAttributeAccessIssue]
                    "QProgressBar { border: 1px solid #ccc; border-radius: 3px; background: #f0f0f0; font-size: 8px; } "
                    "QProgressBar::chunk { background: #2196F3; border-radius: 2px; }"
                )
                main_window.whoosh_index_status = QLabel("全文索引: 0%")  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_status.setStyleSheet("font-size: 9px; color: #2196F3;")  # pyright: ignore[reportAttributeAccessIssue]
                main_window.status_bar.addWidget(main_window.whoosh_index_status)  # pyright: ignore[reportAttributeAccessIssue]
                main_window.status_bar.addWidget(main_window.whoosh_index_progress)  # pyright: ignore[reportAttributeAccessIssue]
            else:
                main_window.whoosh_index_progress.show()  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_status.show()  # pyright: ignore[reportAttributeAccessIssue]
                main_window.whoosh_index_progress.setValue(0)  # pyright: ignore[reportAttributeAccessIssue]
        
        def whoosh_progress_callback(*args):
            try:
                progress_type = args[0] if args else None
                if progress_type == "whoosh" and len(args) == 5:
                    _, drive, progress, indexed, total = args
                    progress_val = max(1, min(round(progress), 100)) if progress > 0 else 0
                    if progress >= 100:
                        status_text = "全文索引: 完成！"
                    elif progress >= 99:
                        status_text = "全文索引: 优化中..."
                    elif progress >= 96:
                        status_text = f"全文索引: 提交中 {progress_val}%"
                    else:
                        status_text = f"全文索引: {progress_val}%"
                    whoosh_signals.update_status.emit(status_text)
                    whoosh_signals.update_progress.emit(progress_val)
                elif len(args) == 3:
                    progress, indexed, total = args
                    progress_val = max(1, min(round(progress), 100)) if progress > 0 else 0
                    whoosh_signals.update_status.emit(f"全文索引: {progress_val}%")
                    whoosh_signals.update_progress.emit(progress_val)
            except Exception as e:
                logger.error(f"Whoosh进度回调错误: {e}")
        
        def build_whoosh_in_background():
            try:
                drives = unified_search_service._detect_indexable_drives()
                search_paths = [f"{d}:\\" for d in drives]
                
                def whoosh_callback(progress, indexed, total):
                    whoosh_progress_callback("whoosh", "ALL", progress, indexed, total)
                
                unified_search_service.fulltext_search.build_index_async(search_paths, whoosh_callback)
                unified_search_service.fulltext_search.build_event.wait()
                
                whoosh_signals.whoosh_complete.emit()
            except Exception as e:
                logger.error(f"Whoosh索引构建失败: {e}")
                whoosh_signals.update_status.emit("全文索引: 失败")
        
        thread = threading.Thread(target=build_whoosh_in_background, daemon=True)
        thread.start()
        
    def _create_completer(self, history_type):
        """
        创建搜索历史下拉提示
        
        Args:
            history_type: 历史类型，可选值："keyword_history"、"directory_history"
            
        Returns:
            QCompleter: 下拉提示组件
        """
        from PySide6.QtWidgets import QCompleter
        from PySide6.QtCore import QStringListModel
        
        # 获取历史记录
        history = self.config.get(history_type, [])
        
        # 创建下拉提示模型
        model = QStringListModel(history)
        completer = QCompleter()
        completer.setModel(model)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        return completer
    
    def _save_search_history(self, keyword, directory):
        """
        保存搜索历史到配置中
        
        Args:
            keyword: 搜索关键字
            directory: 搜索目录
        """
        # 保存搜索关键字历史
        if keyword:
            keyword_history = self.config.get("keyword_history", [])
            # 如果关键字已存在，移到最前面
            if keyword in keyword_history:
                keyword_history.remove(keyword)
            # 添加到最前面
            keyword_history.insert(0, keyword)
            # 保留最近10条历史记录
            keyword_history = keyword_history[:10]
            # 保存到配置
            self.config.set("keyword_history", keyword_history)
            
            # 更新关键字下拉框，但保留当前输入内容
            current_text = self.search_keyword.currentText()  # pyright: ignore[reportOptionalMemberAccess]
            self.search_keyword.clear()  # pyright: ignore[reportOptionalMemberAccess]
            for item in keyword_history:
                self.search_keyword.addItem(item)  # pyright: ignore[reportOptionalMemberAccess]
            # 恢复当前输入内容
            self.search_keyword.setCurrentText(current_text)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 保存搜索目录历史
        if directory:
            directory_history = self.config.get("directory_history", [])
            # 如果目录已存在，移到最前面
            if directory in directory_history:
                directory_history.remove(directory)
            # 添加到最前面
            directory_history.insert(0, directory)
            # 保留最近10条历史记录
            directory_history = directory_history[:10]
            # 保存到配置
            self.config.set("directory_history", directory_history)
            
            # 更新目录下拉框，但保留当前输入内容
            current_text = self.search_directory.currentText()  # pyright: ignore[reportOptionalMemberAccess]
            self.search_directory.clear()  # pyright: ignore[reportOptionalMemberAccess]
            for item in directory_history:
                self.search_directory.addItem(item)  # pyright: ignore[reportOptionalMemberAccess]
            # 恢复当前输入内容
            self.search_directory.setCurrentText(current_text)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _load_search_history(self):
        """
        从配置中加载搜索历史
        """
        # 加载搜索关键字历史
        keyword_history = self.config.get("keyword_history", [])
        # 清空当前的下拉选项
        self.search_keyword.clear()  # pyright: ignore[reportOptionalMemberAccess]
        # 添加历史记录到下拉框
        for keyword in keyword_history:
            self.search_keyword.addItem(keyword)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 加载搜索目录历史
        directory_history = self.config.get("directory_history", [])
        # 清空当前的下拉选项
        self.search_directory.clear()  # pyright: ignore[reportOptionalMemberAccess]
        # 添加历史记录到下拉框
        for directory in directory_history:
            self.search_directory.addItem(directory)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _setup_compare_panel(self):
        """
        设置文件对比面板的UI组件和布局
        """
        from PySide6.QtWidgets import QPushButton, QFileDialog, QCheckBox, QSplitter, QTextEdit, QListWidget
        from PySide6.QtCore import Qt
        
        # 创建对比面板布局
        compare_layout = QVBoxLayout(self.compare_tab)
        
        # 设置布局间距，使控件更加紧凑
        compare_layout.setContentsMargins(5, 5, 5, 5)
        compare_layout.setSpacing(8)
        
        # 文件1选择
        file1_layout = QHBoxLayout()
        file1_layout.setSpacing(5)
        self.file1_edit = QLineEdit()
        self.file1_edit.setPlaceholderText("选择第一个文件或文件夹")
        file1_btn = QPushButton("浏览...")
        file1_btn.setFixedWidth(80)
        file1_btn.clicked.connect(lambda: self._browse_file(self.file1_edit))
        file1_layout.addWidget(self.file1_edit)
        file1_layout.addWidget(file1_btn)
        compare_layout.addLayout(file1_layout)
        
        # 文件2选择
        file2_layout = QHBoxLayout()
        file2_layout.setSpacing(5)
        self.file2_edit = QLineEdit()
        self.file2_edit.setPlaceholderText("选择第二个文件或文件夹")
        file2_btn = QPushButton("浏览...")
        file2_btn.setFixedWidth(80)
        file2_btn.clicked.connect(lambda: self._browse_file(self.file2_edit))
        file2_layout.addWidget(self.file2_edit)
        file2_layout.addWidget(file2_btn)
        compare_layout.addLayout(file2_layout)
        
        # 对比选项
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)
        self.ignore_whitespace = QCheckBox("忽略空格")
        self.ignore_case = QCheckBox("忽略大小写")
        options_layout.addWidget(self.ignore_whitespace)
        options_layout.addWidget(self.ignore_case)
        options_layout.addStretch()
        compare_layout.addLayout(options_layout)
        
        # 对比按钮
        compare_btn = QPushButton("开始对比")
        compare_btn.clicked.connect(self._start_compare)
        compare_layout.addWidget(compare_btn)
        
        # 添加伸缩项，将控件推到顶部
        compare_layout.addStretch()
        
        # 保存对比结果
        self.current_diff_result = None
    
    def _browse_file(self, line_edit):
        """
        浏览文件或文件夹
        
        Args:
            line_edit: 显示选择路径的文本框
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        # 创建一个消息框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择类型")
        msg_box.setText("您要选择文件还是文件夹？")
        
        # 添加自定义按钮
        file_button = msg_box.addButton("文件", QMessageBox.ButtonRole.ActionRole)
        folder_button = msg_box.addButton("文件夹", QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        
        # 设置默认按钮
        msg_box.setDefaultButton(file_button)
        
        # 显示对话框
        msg_box.exec()
        
        # 获取用户选择
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == file_button:
            # 选择文件
            file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", ".")
        elif clicked_button == folder_button:
            # 选择文件夹
            file_path = QFileDialog.getExistingDirectory(self, "选择文件夹", ".")
        else:
            # 取消选择
            file_path = ""
        
        if file_path:
            line_edit.setText(file_path)
    
    def _start_compare(self):
        """
        开始文件对比
        """
        from PySide6.QtWidgets import QMessageBox
        
        file1_path = self.file1_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        file2_path = self.file2_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        
        if not file1_path or not file2_path:
            QMessageBox.warning(self, "警告", "请选择两个文件或文件夹进行对比")
            return
        
        if not os.path.exists(file1_path) or not os.path.exists(file2_path):
            QMessageBox.warning(self, "警告", "选择的文件或文件夹不存在")
            return
        
        # 判断是文件还是文件夹
        is_file1 = os.path.isfile(file1_path)
        is_file2 = os.path.isfile(file2_path)
        
        if is_file1 and is_file2:
            # 文本文件对比
            self._compare_text_files(file1_path, file2_path)
        elif not is_file1 and not is_file2:
            # 文件夹对比
            self._compare_folders(file1_path, file2_path)
        else:
            QMessageBox.warning(self, "警告", "请选择相同类型的项目进行对比（两个文件或两个文件夹）")
    
    def _compare_text_files(self, file1_path, file2_path):
        """
        对比文本文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        """
        # 获取对比选项
        ignore_whitespace = self.ignore_whitespace.isChecked()  # pyright: ignore[reportOptionalMemberAccess]
        ignore_case = self.ignore_case.isChecked()  # pyright: ignore[reportOptionalMemberAccess]
        
        # 执行对比（使用新的compare_files方法）
        diff_result = file_diff_service.compare_files(
            file1_path, file2_path, ignore_whitespace, ignore_case
        )
        
        if diff_result['success']:
            # 保存对比结果
            self.current_diff_result = diff_result
            
            # 显示对比结果对话框
            dialog = CompareResultDialog(diff_result, self)
            dialog.exec()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"对比失败: {diff_result.get('error', '未知错误')}")
    
    def _compare_folders(self, folder1_path, folder2_path):
        """
        对比文件夹
        
        Args:
            folder1_path: 第一个文件夹路径
            folder2_path: 第二个文件夹路径
        """
        # 执行对比
        diff_result = file_diff_service.compare_folders(folder1_path, folder2_path)
        
        if diff_result['success']:
            # 保存对比结果
            self.current_diff_result = diff_result
            
            # 显示对比结果对话框
            dialog = CompareResultDialog(diff_result, self)
            dialog.exec()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"对比失败: {diff_result.get('error', '未知错误')}")
    
    def _setup_transfer_panel(self):
        """
        设置传输面板的UI组件和布局
        """
        from PySide6.QtWidgets import QPushButton, QFileDialog, QCheckBox, QSplitter, QTextEdit, QListWidget, QTableWidget, QTableWidgetItem, QFormLayout, QLineEdit, QComboBox, QProgressBar, QHeaderView, QLabel
        from PySide6.QtCore import Qt, QTimer
        
        # 创建传输面板布局
        transfer_layout = QVBoxLayout(self.transfer_tab)
        
        # 添加FTP连接设置区域
        connection_layout = QFormLayout()
        
        # 主机地址
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("输入FTP服务器地址")
        connection_layout.addRow("主机地址:", self.host_edit)
        
        # 端口
        self.port_edit = QLineEdit()
        self.port_edit.setText("21")
        connection_layout.addRow("端口:", self.port_edit)
        
        # 协议类型
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["ftp", "ftps", "sftp"])
        connection_layout.addRow("协议:", self.protocol_combo)
        
        # 用户名
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("输入用户名")
        connection_layout.addRow("用户名:", self.username_edit)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("输入密码")
        connection_layout.addRow("密码:", self.password_edit)
        
        # 连接按钮
        connect_btn = QPushButton("连接")
        connect_btn.clicked.connect(self._connect_ftp)
        connection_layout.addRow(connect_btn)
        
        transfer_layout.addLayout(connection_layout)
        
        # 添加文件传输区域
        transfer_layout2 = QVBoxLayout()
        
        # 操作类型
        operation_layout = QHBoxLayout()
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["上传", "下载"])
        operation_layout.addWidget(QLabel("操作:"))
        operation_layout.addWidget(self.operation_combo)
        operation_layout.addStretch()
        transfer_layout2.addLayout(operation_layout)
        
        # 本地文件路径
        local_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setPlaceholderText("选择本地文件或文件夹")
        local_btn = QPushButton("浏览...")
        local_btn.clicked.connect(lambda: self._browse_file(self.local_path_edit))
        local_layout.addWidget(self.local_path_edit)
        local_layout.addWidget(local_btn)
        transfer_layout2.addLayout(local_layout)
        
        # 远程文件路径
        remote_layout = QHBoxLayout()
        self.remote_path_edit = QLineEdit()
        self.remote_path_edit.setPlaceholderText("输入远程文件或文件夹路径")
        remote_layout.addWidget(self.remote_path_edit)
        transfer_layout2.addLayout(remote_layout)
        
        # 传输按钮
        transfer_btn = QPushButton("开始传输")
        transfer_btn.clicked.connect(self._start_transfer)
        transfer_layout2.addWidget(transfer_btn)
        
        transfer_layout.addLayout(transfer_layout2)
        
        # 添加传输任务列表
        task_layout = QVBoxLayout()
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels(["任务ID", "操作", "本地路径", "远程路径", "状态", "进度"])
        
        # 设置列宽
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        task_layout.addWidget(self.task_table)
        
        # 任务操作按钮
        task_btn_layout = QHBoxLayout()
        self.refresh_tasks_btn = QPushButton("刷新任务")
        self.refresh_tasks_btn.clicked.connect(self._refresh_tasks)
        self.clear_tasks_btn = QPushButton("清除任务")
        self.clear_tasks_btn.clicked.connect(self._clear_tasks)
        task_btn_layout.addWidget(self.refresh_tasks_btn)
        task_btn_layout.addWidget(self.clear_tasks_btn)
        task_btn_layout.addStretch()
        task_layout.addLayout(task_btn_layout)
        
        transfer_layout.addLayout(task_layout)
        
        # 保存当前连接
        self.current_connection = None
        self.connection_id = None
        
        # 定时刷新任务列表
        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self._refresh_tasks)
        self.task_timer.start(3000)  # 每3秒刷新一次，避免UI卡顿
    
    def _start_p2p_service(self):
        """
        启动P2P服务
        """
        from PySide6.QtWidgets import QMessageBox
        
        try:
            p2p_service.enabled = True
            p2p_service.discover_devices()
            self.start_p2p_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.stop_p2p_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.scan_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.connect_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.send_file_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setText("P2P服务已启动")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: green;")  # pyright: ignore[reportOptionalMemberAccess]
            self._discover_p2p_devices()
        except Exception as e:
            logger.error(f"启动P2P服务失败: {e}")
            QMessageBox.critical(self, "错误", f"启动P2P服务失败: {str(e)}")
    
    def _stop_p2p_service(self):
        """
        停止P2P服务
        """
        from PySide6.QtWidgets import QMessageBox
        
        try:
            p2p_service.enabled = False
            p2p_service.stop_discovery()
            p2p_service.shutdown()
            self.start_p2p_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.stop_p2p_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.scan_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.connect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.send_file_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            # 清空设备列表
            self.device_list.clear()  # pyright: ignore[reportOptionalMemberAccess]
            # 清空任务列表
            self.p2p_task_table.setRowCount(0)  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setText("P2P服务已停止")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: gray;")  # pyright: ignore[reportOptionalMemberAccess]
        except Exception as e:
            logger.error(f"停止P2P服务失败: {e}")
            QMessageBox.critical(self, "错误", f"停止P2P服务失败: {str(e)}")

    def _setup_p2p_panel(self):
        """
        设置P2P传输面板的UI组件和布局
        """
        from PySide6.QtWidgets import QPushButton, QFileDialog, QCheckBox, QSplitter, QTextEdit, QListWidget, QTableWidget, QTableWidgetItem, QFormLayout, QLineEdit, QComboBox, QProgressBar, QHeaderView, QLabel, QGroupBox
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QColor
        
        # 创建P2P传输面板布局
        p2p_layout = QVBoxLayout(self.p2p_tab)
        
        # 创建主分割器（左侧设备连接区，右侧传输任务区）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(1)
        
        # 左侧：设备连接区
        device_group = QGroupBox("设备连接")
        device_layout = QVBoxLayout(device_group)
        
        # P2P服务控制按钮
        service_layout = QHBoxLayout()
        self.start_p2p_btn = QPushButton("启动P2P服务")
        self.start_p2p_btn.clicked.connect(self._start_p2p_service)
        service_layout.addWidget(self.start_p2p_btn)
        
        self.stop_p2p_btn = QPushButton("停止P2P服务")
        self.stop_p2p_btn.clicked.connect(self._stop_p2p_service)
        self.stop_p2p_btn.setEnabled(False)
        service_layout.addWidget(self.stop_p2p_btn)
        device_layout.addLayout(service_layout)
        
        # 扫描设备按钮
        scan_btn = QPushButton("扫描设备")
        scan_btn.clicked.connect(self._discover_p2p_devices)
        scan_btn.setEnabled(False)
        self.scan_btn = scan_btn
        device_layout.addWidget(scan_btn)
        
        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setMinimumHeight(150)
        device_layout.addWidget(self.device_list)
        
        # 连接状态显示
        status_group = QGroupBox("连接状态")
        status_layout = QVBoxLayout(status_group)
        
        self.connection_status_label = QLabel("未连接")
        self.connection_status_label.setStyleSheet("font-size: 14px; color: red;")
        status_layout.addWidget(self.connection_status_label)
        
        self.connection_info_label = QLabel("")
        self.connection_info_label.setStyleSheet("font-size: 12px; color: #666;")
        status_layout.addWidget(self.connection_info_label)
        
        device_layout.addWidget(status_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("请求连接")
        self.connect_btn.clicked.connect(self._request_p2p_connection)
        self.connect_btn.setEnabled(False)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.clicked.connect(self._disconnect_p2p_connection)
        self.disconnect_btn.setEnabled(False)
        button_layout.addWidget(self.disconnect_btn)
        
        self.history_btn = QPushButton("传输历史")
        self.history_btn.clicked.connect(self._view_transfer_history)
        button_layout.addWidget(self.history_btn)
        
        device_layout.addLayout(button_layout)
        
        main_splitter.addWidget(device_group)
        
        # 右侧：传输任务区
        task_group = QGroupBox("传输任务")
        task_layout = QVBoxLayout(task_group)
        
        # 当前连接信息
        current_conn_group = QGroupBox("当前连接")
        current_conn_layout = QVBoxLayout(current_conn_group)
        
        self.current_connection_label = QLabel("未连接到任何设备")
        current_conn_layout.addWidget(self.current_connection_label)
        
        task_layout.addWidget(current_conn_group)
        
        # 传输控制
        control_layout = QHBoxLayout()
        
        self.send_file_btn = QPushButton("发送文件")
        self.send_file_btn.clicked.connect(self._browse_p2p_file)
        self.send_file_btn.setEnabled(False)
        control_layout.addWidget(self.send_file_btn)
        
        self.receive_settings_btn = QPushButton("接收设置")
        self.receive_settings_btn.clicked.connect(self._open_receive_settings)
        control_layout.addWidget(self.receive_settings_btn)
        
        control_layout.addStretch()
        task_layout.addLayout(control_layout)
        
        # 任务列表
        self.p2p_task_table = QTableWidget()
        self.p2p_task_table.setColumnCount(6)
        self.p2p_task_table.setHorizontalHeaderLabels(["方向", "文件名", "进度", "速度", "剩余时间", "操作"])
        
        # 设置列宽
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.p2p_task_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        task_layout.addWidget(self.p2p_task_table)
        
        # 任务详情面板（默认隐藏）
        self.task_detail_group = QGroupBox("任务详情")
        self.task_detail_group.setVisible(False)
        task_detail_layout = QVBoxLayout(self.task_detail_group)
        
        self.task_detail_info = QTextEdit()
        self.task_detail_info.setReadOnly(True)
        self.task_detail_info.setMinimumHeight(150)
        task_detail_layout.addWidget(self.task_detail_info)
        
        task_detail_control = QHBoxLayout()
        
        self.p2p_pause_btn = QPushButton("暂停")
        self.p2p_pause_btn.clicked.connect(self._pause_p2p_transfer)
        self.p2p_pause_btn.setEnabled(False)
        task_detail_control.addWidget(self.p2p_pause_btn)
        
        self.p2p_resume_btn = QPushButton("继续")
        self.p2p_resume_btn.clicked.connect(self._resume_p2p_transfer)
        self.p2p_resume_btn.setEnabled(False)
        task_detail_control.addWidget(self.p2p_resume_btn)
        
        self.p2p_cancel_btn = QPushButton("取消")
        self.p2p_cancel_btn.clicked.connect(self._cancel_p2p_transfer)
        self.p2p_cancel_btn.setEnabled(False)
        task_detail_control.addWidget(self.p2p_cancel_btn)
        
        self.hide_detail_btn = QPushButton("隐藏详情")
        self.hide_detail_btn.clicked.connect(lambda: self.task_detail_group.setVisible(False))  # pyright: ignore[reportOptionalMemberAccess]
        task_detail_control.addWidget(self.hide_detail_btn)
        
        task_detail_control.addStretch()
        task_detail_layout.addLayout(task_detail_control)
        
        task_layout.addWidget(self.task_detail_group)
        
        main_splitter.addWidget(task_group)
        main_splitter.setSizes([300, 500])  # 设置初始大小
        
        p2p_layout.addWidget(main_splitter)
        
        # 初始化P2P相关变量
        self.current_p2p_file = None
        self.current_p2p_files = []
        self.current_p2p_task_id = None
        self.connection_status = False
        self.p2p_current_connection = None
        self.transfer_request_dialog = None
        self.selected_device = None
        
        # 设置P2P传输请求回调
        p2p_service.set_transfer_request_callback(self._on_transfer_request)
        
        # 定时刷新设备列表
        self.device_scan_timer = QTimer(self)
        self.device_scan_timer.timeout.connect(self._discover_p2p_devices)
        self.device_scan_timer.start(8000)  # 每8秒扫描一次，减少网络和CPU占用
        
        # 定时刷新任务列表
        self.task_refresh_timer = QTimer(self)
        self.task_refresh_timer.timeout.connect(self._refresh_p2p_tasks)
        self.task_refresh_timer.start(2000)  # 每2秒刷新一次，减少UI刷新频率，提高界面流畅度
        
        # 初始化设备列表
        # 暂时不自动扫描，等待用户启动服务
    

    
    def _connect_ftp(self):
        """
        连接到FTP服务器
        """
        from PySide6.QtWidgets import QMessageBox
        
        host = self.host_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        port = self.port_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        protocol = self.protocol_combo.currentText()  # pyright: ignore[reportOptionalMemberAccess]
        username = self.username_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        password = self.password_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        
        if not host or not port or not username:
            QMessageBox.warning(self, "警告", "请填写完整的连接信息")
            return
        
        try:
            port = int(port)
        except ValueError:
            QMessageBox.warning(self, "警告", "端口号必须是数字")
            return
        
        # 创建FTP连接
        self.connection_id = ftp_service.create_connection(
            host, port, username, password, protocol
        )
        
        # 连接到服务器
        success = ftp_service.connect(self.connection_id)
        
        if success:
            self.current_connection = ftp_service.get_connection(self.connection_id)
            QMessageBox.information(self, "成功", "连接到FTP服务器成功")
        else:
            QMessageBox.critical(self, "错误", "连接到FTP服务器失败")
    
    def _start_transfer(self):
        """
        开始文件传输
        """
        from PySide6.QtWidgets import QMessageBox
        import os
        
        if not self.current_connection:
            QMessageBox.warning(self, "警告", "请先连接到FTP服务器")
            return
        
        operation = self.operation_combo.currentText()  # pyright: ignore[reportOptionalMemberAccess]
        local_path = self.local_path_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        remote_path = self.remote_path_edit.text().strip()  # pyright: ignore[reportOptionalMemberAccess]
        
        if not local_path or not remote_path:
            QMessageBox.warning(self, "警告", "请填写完整的文件路径")
            return
        
        # 检查本地路径是否存在
        if not os.path.exists(local_path):
            QMessageBox.warning(self, "警告", "本地路径不存在")
            return
        
        # 转换操作类型
        if operation == "上传":
            op = "upload"
            # 上传时检查本地路径是文件还是文件夹
            is_folder = os.path.isdir(local_path)
            if is_folder and not remote_path.endswith('/'):
                remote_path += '/'  # 确保远程路径以/结尾
        else:
            op = "download"
        
        # 开始传输任务
        task_id = ftp_service.start_transfer(
            op, local_path, remote_path, self.current_connection
        )
        
        file_type = "文件夹" if os.path.isdir(local_path) else "文件"
        QMessageBox.information(self, "成功", f"{file_type}传输任务已添加，任务ID: {task_id}")
        self._refresh_tasks()
    
    def _refresh_tasks(self):
        """
        刷新传输任务列表
        """
        # 清空任务表  # pyright: ignore[reportOptionalMemberAccess]
        self.task_table.setRowCount(0)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 获取所有任务
        tasks = ftp_service.get_all_transfer_tasks()
        
        # 添加任务到表格
        for task in tasks:
            row = self.task_table.rowCount()  # pyright: ignore[reportOptionalMemberAccess]
            self.task_table.insertRow(row)  # pyright: ignore[reportOptionalMemberAccess]
            
            # 任务ID
            self.task_table.setItem(row, 0, QTableWidgetItem(task.task_id))  # pyright: ignore[reportOptionalMemberAccess]
            
            # 操作类型
            operation = "上传" if task.operation == "upload" else "下载"
            self.task_table.setItem(row, 1, QTableWidgetItem(operation))  # pyright: ignore[reportOptionalMemberAccess]
            
            # 本地路径
            self.task_table.setItem(row, 2, QTableWidgetItem(task.local_path))  # pyright: ignore[reportOptionalMemberAccess]
            
            # 远程路径
            self.task_table.setItem(row, 3, QTableWidgetItem(task.remote_path))  # pyright: ignore[reportOptionalMemberAccess]
            
            # 状态
            status_map = {
                "pending": "等待中",
                "running": "传输中",
                "completed": "已完成",
                "failed": "失败",
                "cancelled": "已取消"
            }
            status = status_map.get(task.status, task.status)
            self.task_table.setItem(row, 4, QTableWidgetItem(status))  # pyright: ignore[reportOptionalMemberAccess]
            
            # 进度
            progress_item = QTableWidgetItem()
            if task.total_size > 0:
                progress = int((task.progress / task.total_size) * 100)
                progress_item.setText(f"{progress}%")
            else:
                # 文件夹或未知大小的文件
                if task.is_folder:
                    progress_item.setText("文件夹")
                else:
                    progress_item.setText("0%")
            self.task_table.setItem(row, 5, progress_item)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _clear_tasks(self):
        """
        清除传输任务
        """
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "确认", "确定要清除所有已完成、失败或已取消的任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清除FTP服务中的任务
            ftp_service.clear_tasks()
            # 清空UI显示
            self.task_table.setRowCount(0)  # pyright: ignore[reportOptionalMemberAccess]
    

    

    
    def _browse_search_directory(self):
        """
        浏览搜索目录
        """
        from PySide6.QtWidgets import QFileDialog
        
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(self, "选择搜索目录", ".")
        if directory:
            self.search_directory.setCurrentText(directory)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _start_search(self):
        """
        开始搜索
        """
        # 获取搜索条件
        keyword = self.search_keyword.currentText()  # pyright: ignore[reportOptionalMemberAccess]
        directory = self.search_directory.currentText()  # pyright: ignore[reportOptionalMemberAccess]
        include_subdirectories = self.include_subdirectories.isChecked()  # pyright: ignore[reportOptionalMemberAccess]
        search_content = self.search_content.isChecked()  # pyright: ignore[reportOptionalMemberAccess]
        file_type = self.file_type_combo.currentText()  # pyright: ignore[reportOptionalMemberAccess]
        
        if search_content:
            from services.unified_search_service import unified_search_service
            if unified_search_service.fulltext_search.is_indexing:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "全文索引构建中",
                    "Whoosh 全文索引正在后台构建中，请稍后再试。\n\n"
                    "当前可使用文件名搜索功能。"
                )
                return
            if not unified_search_service.fulltext_search.index_built:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, "全文索引未构建",
                    "全文搜索索引尚未构建，是否现在构建？\n\n"
                    "（构建完成后搜索速度提升100-1000倍）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._build_search_index_with_progress()
                return
        
        # 检查目录是否存在
        if not directory:
            show_warning(self, "警告", "请选择有效的搜索目录")
            return
        
        # 确定文件类型
        file_types = None
        if file_type != "所有文件":
            # 映射文件类型到扩展名列表
            type_mapping = {
                "文本文件": ['.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini', '.csv', '.md'],
                "图片文件": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
                "文档文件": ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'],
                "压缩文件": ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
                "音频文件": ['.mp3', '.wav', '.ogg'],
                "视频文件": ['.mp4', '.avi', '.mov', '.mkv']
            }
            file_types = type_mapping.get(file_type, None)
        
        # 如果勾选了搜索文件内容选项，只搜索文本及文档文件类型
        if search_content:
            # 文本文件类型
            text_file_types = ['.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini', '.csv', '.md',
                             '.html', '.css', '.js', '.xml', '.sql', '.java', '.c', '.cpp', '.h', '.hpp',
                             '.php', '.rb', '.go']
            # 文档文件类型
            doc_file_types = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
            # 合并文本和文档文件类型
            text_doc_file_types = text_file_types + doc_file_types
            
            # 如果用户选择了文件类型，只保留其中的文本和文档文件类型
            if file_types:
                # 筛选出用户选择的文件类型中的文本和文档文件类型
                file_types = [ft for ft in file_types if ft in text_doc_file_types]
            else:
                # 如果没有选择文件类型，默认只搜索所有文本和文档文件类型
                file_types = text_doc_file_types
        
        # 保存搜索历史
        self._save_search_history(keyword, directory)
        
        # 执行搜索（使用异步执行，避免主窗口无响应）
        from PySide6.QtCore import QThreadPool, QRunnable, Slot, QObject, Signal
        
        # 创建一个信号载体类
        class SearchResultSignals(QObject):
            results_ready = Signal(list)
            progress_updated = Signal(str, int, int, int, int)  # 添加进度更新信号: progress_text, progress_value, processed_files, total_files, success_count
        
        signals = SearchResultSignals()
        
        # 连接信号到槽函数
        def handle_results(results):
            # 搜索完成，重置进度显示
            self.progress_label.setText("搜索完成")  # pyright: ignore[reportOptionalMemberAccess]
            self.progress_bar.setVisible(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.current_file_label.setText("搜索完成")  # pyright: ignore[reportOptionalMemberAccess]
            
            if results:
                search_info = {
                    'keyword': keyword,
                    'directory': directory,
                    'include_subdirectories': include_subdirectories,
                    'search_content': search_content,
                    'file_type': file_type
                }
                dialog = SearchResultDialog(results, search_info, self)
                dialog.exec()
            else:
                show_info(self, "搜索完成", "没有找到匹配的文件")
        
        def handle_progress(progress_text, progress_value, processed_files, total_files, success_count):
            # 更新进度显示
            self.progress_label.setText(progress_text)  # pyright: ignore[reportOptionalMemberAccess]
            self.progress_bar.setValue(progress_value)  # pyright: ignore[reportOptionalMemberAccess]
            
            # 更新统计信息
            if progress_text.startswith("正在搜索"):
                # 提取当前文件名
                file_name = progress_text.replace("正在搜索: ", "").replace("正在搜索 ", "")
                self.current_file_label.setText(f"正在搜索: {file_name}")  # pyright: ignore[reportOptionalMemberAccess]
            
            self.searched_count_label.setText(f"已搜索: {processed_files}")  # pyright: ignore[reportOptionalMemberAccess]
            self.total_files_label.setText(f"总文件: {total_files}")  # pyright: ignore[reportOptionalMemberAccess]
            self.success_count_label.setText(f"已找到: {success_count}")  # pyright: ignore[reportOptionalMemberAccess]
        
        signals.results_ready.connect(handle_results)
        signals.progress_updated.connect(handle_progress)
        
        # 显示进度条
        self.progress_bar.setVisible(True)  # pyright: ignore[reportOptionalMemberAccess]
        self.progress_label.setText("正在搜索...")  # pyright: ignore[reportOptionalMemberAccess]
        self.progress_bar.setValue(0)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 初始化统计信息
        self.current_file_label.setText("准备搜索...")  # pyright: ignore[reportOptionalMemberAccess]
        self.searched_count_label.setText("已搜索: 0")  # pyright: ignore[reportOptionalMemberAccess]
        self.total_files_label.setText("总文件: 0")  # pyright: ignore[reportOptionalMemberAccess]
        self.success_count_label.setText("已找到: 0")  # pyright: ignore[reportOptionalMemberAccess]
        
        class SearchRunnable(QRunnable):
            def __init__(self, keyword, directory, include_subdirectories, search_content, file_types, signals, function_panel):
                super().__init__()
                self.keyword = keyword
                self.directory = directory
                self.include_subdirectories = include_subdirectories
                self.search_content = search_content
                self.file_types = file_types
                self.signals = signals
                self.function_panel = function_panel

            
            @Slot()
            def run(self):
                from services.unified_search_service import unified_search_service
                try:
                    if self.function_panel.search_stopped:
                        self.signals.progress_updated.emit("搜索已取消", 100, 0, 0, 0)
                        self.signals.results_ready.emit([])
                        return
                    
                    if self.search_content and self.keyword:
                        self.signals.progress_updated.emit("正在执行全文搜索...", 50, 0, 100, 0)
                        results = unified_search_service.search(
                            keyword=self.keyword,
                            search_type="content",
                            max_results=1000,
                            directory=self.directory
                        )
                    else:
                        self.signals.progress_updated.emit("正在执行快速搜索...", 50, 0, 100, 0)
                        results = unified_search_service.search(
                            keyword=self.keyword,
                            search_type="filename",
                            max_results=1000,
                            directory=self.directory
                        )
                    
                    if self.function_panel.search_stopped:
                        self.signals.progress_updated.emit("搜索已取消", 100, 0, 0, 0)
                        self.signals.results_ready.emit([])
                        return
                    

                    self.signals.progress_updated.emit("搜索完成", 100, len(results), len(results), len(results))
                    
                except Exception as e:
                    logger.error(f"搜索失败: {e}")
                    self.signals.progress_updated.emit(f"搜索失败: {e}", 100, 0, 0, 0)
                    results = []
                finally:
                    # 搜索结束，重置状态
                    self.function_panel.search_stopped = False
                    self.function_panel.search_paused = False
                    # 启用/禁用按钮
                    self.function_panel.pause_btn.setEnabled(False)
                    self.function_panel.stop_btn.setEnabled(False)
                
                # 发送信号，在主线程中显示结果
                self.signals.results_ready.emit(results)
            
            def _progress_callback(self, current_file, total_files, progress_text, success_count):
                # 初始化历史最大总文件数
                if not hasattr(self, '_max_total_files'):
                    self._max_total_files = 0  # pyright: ignore[reportUninitializedInstanceVariable]
                
                # 更新历史最大总文件数，确保它只增加不减少
                if total_files > self._max_total_files:
                    self._max_total_files = total_files
                
                # 使用历史最大总文件数计算进度，确保进度平滑增加
                if self._max_total_files > 0:
                    progress = int((current_file / self._max_total_files) * 100)
                else:
                    progress = 0
                
                # 确保进度不超过100%
                progress = min(progress, 100)
                
                # 发送进度更新信号，使用从搜索服务传来的success_count
                self.signals.progress_updated.emit(progress_text, progress, current_file, self._max_total_files, success_count)
        
        # 保存当前搜索任务
        self.search_runnable = SearchRunnable(keyword, directory, include_subdirectories, search_content, file_types, signals, self)
        
        # 启用暂停和停止按钮
        self.pause_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
        self.stop_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 启动搜索线程
        QThreadPool.globalInstance().start(self.search_runnable)
    

    
    def _pause_search(self):
        """
        暂停或恢复搜索
        """
        self.search_paused = not self.search_paused
        
        if self.search_paused:
            self.pause_btn.setText("恢复搜索")  # pyright: ignore[reportOptionalMemberAccess]
            self.progress_label.setText("搜索已暂停")  # pyright: ignore[reportOptionalMemberAccess]
        else:
            self.pause_btn.setText("暂停搜索")  # pyright: ignore[reportOptionalMemberAccess]
            self.progress_label.setText("正在搜索...")  # pyright: ignore[reportOptionalMemberAccess]
    
    def _stop_search(self):
        """
        停止搜索
        """
        self.search_stopped = True
        self.search_paused = False
        
        # 重置按钮状态
        self.pause_btn.setText("暂停搜索")  # pyright: ignore[reportOptionalMemberAccess]
        self.pause_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
        self.stop_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 更新进度显示
        self.progress_label.setText("搜索已停止")  # pyright: ignore[reportOptionalMemberAccess]
        self.progress_bar.setVisible(False)  # pyright: ignore[reportOptionalMemberAccess]
    
    def update_preview(self, file_path):
        """
        更新预览内容
        
        Args:
            file_path: 文件路径
        """
        # 检查是否为文件
        if not os.path.isfile(file_path):
            # 隐藏文件信息标签
            self.preview_file_info.setVisible(False)  # pyright: ignore[reportOptionalMemberAccess]
            
            # 清除当前预览内容
            for i in reversed(range(self.preview_content_layout.count())):  # pyright: ignore[reportOptionalMemberAccess]
                widget = self.preview_content_layout.itemAt(i).widget()  # pyright: ignore[reportOptionalMemberAccess]
                if widget is not None:
                    widget.setParent(None)
            
            # 显示默认提示
            self.preview_content_layout.addWidget(self.default_preview_label)  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
            # 切换到预览标签页
            self.setCurrentIndex(2)  # 预览标签页索引为2
            return
        
        # 保存当前预览的文件路径
        self.current_preview_file = file_path
        
        # 设置文件信息标签内容
        file_name = os.path.basename(file_path)
        self.preview_file_info.setText(f"文件: {file_name}\n路径: {file_path}")  # pyright: ignore[reportOptionalMemberAccess]
        self.preview_file_info.setVisible(True)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 清除当前预览内容
        for i in reversed(range(self.preview_content_layout.count())):  # pyright: ignore[reportOptionalMemberAccess]
            widget = self.preview_content_layout.itemAt(i).widget()  # pyright: ignore[reportOptionalMemberAccess]
            if widget is not None:
                widget.setParent(None)
        
        # 生成新的预览内容（使用新的预览服务）
        preview_widget = preview_service.preview(file_path, self.preview_content)  # pyright: ignore[reportArgumentType]
        if preview_widget:
            self.preview_content_layout.addWidget(preview_widget)  # pyright: ignore[reportOptionalMemberAccess]
        else:
            # 如果无法预览，显示默认提示
            self.preview_content_layout.addWidget(self.default_preview_label)  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
        
        # 切换到预览标签页
        self.setCurrentIndex(2)  # 预览标签页索引为2
    
    def _on_preview_double_click(self, event):
        """
        处理预览内容区域的双击事件，在新弹出的窗口中显示预览内容
        
        Args:
            event: 鼠标事件
        """
        # 检查当前是否有文件正在预览
        if not hasattr(self, 'current_preview_file') or not self.current_preview_file:
            return
        
        # 获取当前预览的文件路径
        file_path = self.current_preview_file
        
        # 创建新的弹出窗口
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"预览: {os.path.basename(file_path)}")
        dialog.setMinimumSize(800, 600)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 生成预览内容，继承原预览的所有功能特性
        preview_widget = preview_service.preview_file(file_path, dialog)
        
        # 添加到布局
        layout.addWidget(preview_widget)
        
        # 显示窗口
        dialog.exec()
        
        # 显式清理资源
        try:
            # 检查preview_widget是否有_cleanup_resources方法
            if hasattr(preview_widget, '_cleanup_resources'):
                preview_widget._cleanup_resources()  # pyright: ignore[reportAttributeAccessIssue]
            # 检查preview_widget是否有handler属性，handler可能有_cleanup_resources方法
            elif hasattr(preview_widget, 'handler') and hasattr(preview_widget.handler, '_cleanup_resources'):  # pyright: ignore[reportAttributeAccessIssue]
                preview_widget.handler._cleanup_resources()  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as e:
            # 即使发生错误也继续执行
            pass
    
    def connect_file_selection(self, left_pane, right_pane):
        """
        连接文件选择信号
        
        Args:
            left_pane: 左侧窗格
            right_pane: 右侧窗格
        """
    
    def dragEnterEvent(self, event):
        """
        处理拖拽进入事件
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """
        处理拖拽移动事件
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """
        处理拖拽释放事件
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.update_preview(file_path)
                    break
            event.acceptProposedAction()

    
    def _on_file_selected(self, pane, index):
        """
        文件被选择时的处理
        
        Args:
            pane: 所属窗格
            index: 选中的文件索引
        """
        import os
        
        # 将代理模型的索引转换为源模型的索引
        source_index = pane.proxy_model.mapToSource(index)
        file_path = pane.model.filePath(source_index)
        
        # 检查是否为文件
        if not os.path.isfile(file_path):
            return
        
        # 更新预览
        self.update_preview(file_path)
    
    def switch_to_tab(self, tab_name):
        """
        切换到指定标签页
        
        Args:
            tab_name: 标签页名称，可选值："搜索"、"对比"、"预览"、"传输"、"Ftp"、"P2P"、"辅助"
        """
        # 切换到指定标签页
        tab_map = {
            "搜索": 0,
            "对比": 1,
            "预览": 2,
            "传输": 3,
            "Ftp": 3,
            "P2P": 4,
            "辅助": 5
        }
        if tab_name in tab_map:
            self.setCurrentIndex(tab_map[tab_name])
    
    def _setup_tools_panel(self):
        """
        设置辅助工具面板的UI组件和布局
        """
        from PySide6.QtWidgets import (QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, 
                                    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
                                    QFormLayout, QGroupBox, QTabWidget, QTextEdit, QProgressBar)
        from PySide6.QtCore import Qt
        
        # 创建辅助工具面板布局
        tools_layout = QVBoxLayout(self.tools_tab)
        
        # 创建工具标签页
        self.tools_tab_widget = QTabWidget()
        
        # 批量重命名标签页
        rename_tab = QWidget()
        self._setup_batch_rename_tab(rename_tab)
        self.tools_tab_widget.addTab(rename_tab, "批量重命名")
        
        # 文件编码转换标签页
        encoding_tab = QWidget()
        self._setup_encoding_convert_tab(encoding_tab)
        self.tools_tab_widget.addTab(encoding_tab, "编码转换")
        
        # 图片格式转换标签页
        image_tab = QWidget()
        self._setup_image_convert_tab(image_tab)
        self.tools_tab_widget.addTab(image_tab, "图片转换")
        
        # 文件校验标签页
        verify_tab = QWidget()
        self._setup_file_verify_tab(verify_tab)
        self.tools_tab_widget.addTab(verify_tab, "文件校验")
        
        # 文件合并标签页
        merge_tab = QWidget()
        self._setup_file_merge_tab(merge_tab)  # pyright: ignore[reportAttributeAccessIssue]
        self.tools_tab_widget.addTab(merge_tab, "文件合并")
        
        tools_layout.addWidget(self.tools_tab_widget)
    
    def _setup_batch_rename_tab(self, parent):
        """
        设置批量重命名标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.rename_files_label = QLabel("未选择文件")
        self.rename_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.rename_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_rename_files)
        file_layout.addWidget(self.rename_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 重命名规则区域
        rule_group = QGroupBox("重命名规则")
        rule_layout = QFormLayout(rule_group)
        
        self.rename_type_combo = QComboBox()
        self.rename_type_combo.addItems(["添加前缀", "添加后缀", "替换文本", "添加序号"])
        rule_layout.addRow("重命名类型:", self.rename_type_combo)
        
        # 前缀设置
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("输入前缀")
        rule_layout.addRow("前缀:", self.prefix_edit)
        
        # 后缀设置
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("输入后缀")
        rule_layout.addRow("后缀:", self.suffix_edit)
        
        # 替换文本设置
        self.old_text_edit = QLineEdit()
        self.old_text_edit.setPlaceholderText("输入要替换的文本")
        rule_layout.addRow("旧文本:", self.old_text_edit)
        
        self.new_text_edit = QLineEdit()
        self.new_text_edit.setPlaceholderText("输入新文本")
        rule_layout.addRow("新文本:", self.new_text_edit)
        
        # 序号设置
        self.start_edit = QLineEdit("1")
        rule_layout.addRow("起始序号:", self.start_edit)  # pyright: ignore[reportArgumentType]
        
        self.padding_edit = QLineEdit("3")
        rule_layout.addRow("序号填充:", self.padding_edit)  # pyright: ignore[reportArgumentType]
        
        layout.addWidget(rule_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.rename_preview = QTextEdit()
        self.rename_preview.setReadOnly(True)
        preview_layout.addWidget(self.rename_preview)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self._preview_rename)
        execute_btn = QPushButton("执行")
        execute_btn.clicked.connect(self._execute_rename)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(execute_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.rename_files = []
    
    def _browse_rename_files(self):
        """
        选择要重命名的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.rename_files = files
            self.rename_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _preview_rename(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        预览重命名结果
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.rename_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            rename_type = self.rename_type_combo.currentText()
            
            if rename_type == "添加前缀":
                prefix = self.prefix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "prefix", prefix=prefix)
            elif rename_type == "添加后缀":
                suffix = self.suffix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "suffix", suffix=suffix)
            elif rename_type == "替换文本":
                old_text = self.old_text_edit.text().strip()
                new_text = self.new_text_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "replace", old_text=old_text, new_text=new_text)
            elif rename_type == "添加序号":
                start = int(self.start_edit.text().strip() or "1")
                padding = int(self.padding_edit.text().strip() or "3")
                rename_map = tools_service.batch_rename(self.rename_files, "serial", start=start, padding=padding)
            else:
                QMessageBox.warning(self, "警告", "不支持的重命名类型")
                return
            
            # 显示预览结果
            preview_text = "重命名预览:\n\n"
            for old_path, new_path in rename_map.items():
                preview_text += f"{os.path.basename(old_path)} → {os.path.basename(new_path)}\n"
            
            self.rename_preview.setText(preview_text)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览失败: {str(e)}")
    
    def _execute_rename(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行批量重命名
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.rename_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            rename_type = self.rename_type_combo.currentText()
            
            if rename_type == "添加前缀":
                prefix = self.prefix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "prefix", prefix=prefix)
            elif rename_type == "添加后缀":
                suffix = self.suffix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "suffix", suffix=suffix)
            elif rename_type == "替换文本":
                old_text = self.old_text_edit.text().strip()
                new_text = self.new_text_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "replace", old_text=old_text, new_text=new_text)
            elif rename_type == "添加序号":
                start = int(self.start_edit.text().strip() or "1")
                padding = int(self.padding_edit.text().strip() or "3")
                rename_map = tools_service.batch_rename(self.rename_files, "serial", start=start, padding=padding)
            else:
                QMessageBox.warning(self, "警告", "不支持的重命名类型")
                return
            
            # 执行重命名
            failed = tools_service.execute_rename(rename_map)
            
            if failed:
                QMessageBox.warning(self, "警告", f"部分文件重命名失败: {len(failed)} 个文件")
            else:
                QMessageBox.information(self, "成功", f"成功重命名 {len(rename_map)} 个文件")
                self.rename_files = []
                self.rename_files_label.setText("未选择文件")
                self.rename_preview.clear()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行失败: {str(e)}")
    
    def _setup_encoding_convert_tab(self, parent):
        """
        设置文件编码转换标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.encoding_files_label = QLabel("未选择文件")
        self.encoding_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.encoding_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_encoding_files)
        file_layout.addWidget(self.encoding_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 编码设置区域
        encode_layout = QFormLayout()
        self.target_encoding_combo = QComboBox()
        self.target_encoding_combo.addItems(["utf-8", "gbk", "ascii", "utf-16", "utf-32"])
        encode_layout.addRow("目标编码:", self.target_encoding_combo)
        
        self.backup_checkbox = QCheckBox("备份原文件")
        self.backup_checkbox.setChecked(True)
        encode_layout.addRow(self.backup_checkbox)
        layout.addLayout(encode_layout)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.encoding_preview = QTextEdit()
        self.encoding_preview.setReadOnly(True)
        preview_layout.addWidget(self.encoding_preview)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        detect_btn = QPushButton("检测编码")
        detect_btn.clicked.connect(self._detect_encoding)
        convert_btn = QPushButton("转换")
        convert_btn.clicked.connect(self._execute_encoding_convert)
        btn_layout.addWidget(detect_btn)
        btn_layout.addWidget(convert_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.encoding_files = []
    
    def _browse_encoding_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要转换编码的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.encoding_files = files
            self.encoding_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _detect_encoding(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        检测文件编码
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.encoding_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            result = "文件编码检测结果:\n\n"
            for file_path in self.encoding_files:
                encoding = tools_service.detect_encoding(file_path)
                result += f"{os.path.basename(file_path)}: {encoding}\n"
            
            self.encoding_preview.setText(result)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检测编码失败: {str(e)}")
    
    def _execute_encoding_convert(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行文件编码转换
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.encoding_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            target_encoding = self.target_encoding_combo.currentText()
            backup = self.backup_checkbox.isChecked()
            
            results = tools_service.convert_encoding(self.encoding_files, target_encoding, backup)
            
            # 显示结果
            result_text = "编码转换结果:\n\n"
            for file_path, status in results.items():
                result_text += f"{os.path.basename(file_path)}: {status}\n"
            
            self.encoding_preview.setText(result_text)
            QMessageBox.information(self, "成功", "编码转换完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败: {str(e)}")
    
    def _setup_image_convert_tab(self, parent):
        """
        设置图片格式转换标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.image_files_label = QLabel("未选择文件")
        self.image_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.image_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_image_files)
        file_layout.addWidget(self.image_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 转换设置区域
        convert_layout = QFormLayout()
        self.target_format_combo = QComboBox()
        self.target_format_combo.addItems(["jpg", "png", "gif", "bmp", "webp"])
        convert_layout.addRow("目标格式:", self.target_format_combo)  # pyright: ignore[reportArgumentType]
        
        self.quality_edit = QLineEdit("85")
        convert_layout.addRow("图片质量:", self.quality_edit)
        
        self.overwrite_checkbox = QCheckBox("覆盖原文件")
        convert_layout.addRow(self.overwrite_checkbox)
        layout.addLayout(convert_layout)
        
        # 预览区域
        preview_group = QGroupBox("图片信息")
        preview_layout = QVBoxLayout(preview_group)
        
        self.image_info_text = QTextEdit()
        self.image_info_text.setReadOnly(True)
        preview_layout.addWidget(self.image_info_text)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        info_btn = QPushButton("查看信息")
        info_btn.clicked.connect(self._show_image_info)
        convert_btn = QPushButton("转换")
        convert_btn.clicked.connect(self._execute_image_convert)
        btn_layout.addWidget(info_btn)
        btn_layout.addWidget(convert_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.image_files = []
    
    def _browse_image_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要转换的图片文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", ".", "图片文件 (*.jpg *.jpeg *.png *.gif *.bmp *.webp)")
        if files:
            self.image_files = files
            self.image_files_label.setText(f"已选择 {len(files)} 个图片")
    
    def _show_image_info(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        显示图片信息
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.image_files:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return
        
        try:
            result = "图片信息:\n\n"
            for file_path in self.image_files:
                info = tools_service.get_image_info(file_path)
                result += f"{os.path.basename(file_path)}:\n"
                for key, value in info.items():
                    result += f"  {key}: {value}\n"
                result += "\n"
            
            self.image_info_text.setText(result)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取信息失败: {str(e)}")
    
    def _execute_image_convert(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行图片格式转换
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.image_files:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return
        
        try:
            target_format = self.target_format_combo.currentText()
            quality = int(self.quality_edit.text())
            overwrite = self.overwrite_checkbox.isChecked()
            
            results = tools_service.convert_image_format(self.image_files, target_format, quality, overwrite=overwrite)
            
            # 显示结果
            result_text = "图片转换结果:\n\n"
            for file_path, status in results.items():
                result_text += f"{os.path.basename(file_path)}: {status}\n"
            
            self.image_info_text.setText(result_text)
            QMessageBox.information(self, "成功", "图片转换完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败: {str(e)}")
    
    def _setup_file_verify_tab(self, parent):
        """
        设置文件校验标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.verify_files_label = QLabel("未选择文件")
        self.verify_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.verify_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_verify_files)
        file_layout.addWidget(self.verify_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 算法选择区域
        algo_layout = QFormLayout()
        self.hash_algo_combo = QComboBox()
        self.hash_algo_combo.addItems(["md5", "sha1", "sha256"])
        algo_layout.addRow("哈希算法:", self.hash_algo_combo)
        layout.addLayout(algo_layout)
        
        # 校验结果区域
        result_group = QGroupBox("校验结果")
        result_layout = QVBoxLayout(result_group)
        
        self.verify_result_text = QTextEdit()
        self.verify_result_text.setReadOnly(True)
        result_layout.addWidget(self.verify_result_text)
        layout.addWidget(result_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        calculate_btn = QPushButton("计算哈希")
        calculate_btn.clicked.connect(self._calculate_file_hash)
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self._export_verify_report)
        btn_layout.addWidget(calculate_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.verify_files = []
    
    def _browse_verify_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要校验的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.verify_files = files
            self.verify_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _calculate_file_hash(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        计算文件哈希值
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.verify_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            algorithm = self.hash_algo_combo.currentText()
            hashes = tools_service.calculate_file_hash(self.verify_files, algorithm)
            
            # 显示结果
            result_text = f"文件{algorithm.upper()}校验结果:\n\n"
            for file_path, hash_value in hashes.items():
                result_text += f"{os.path.basename(file_path)}: {hash_value}\n"
            
            self.verify_result_text.setText(result_text)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算哈希失败: {str(e)}")
    
    def _export_verify_report(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        导出校验报告
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.verify_files:
            QMessageBox.warning(self, "警告", "请先选择文件并计算哈希")
            return
        
        try:
            algorithm = self.hash_algo_combo.currentText()
            report = tools_service.generate_verification_report(self.verify_files, algorithm)
            
            # 保存报告到文件
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(self, "导出报告", f"verify_report.txt", "文本文件 (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                QMessageBox.information(self, "成功", f"报告已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def add_files_to_verify(self, file_paths):
        """
        将文件添加到文件校验的文件输入框内
        
        Args:
            file_paths: 文件路径列表
        """
        if file_paths:
            # 更新文件列表和标签
            self.verify_files = file_paths
            self.verify_files_label.setText(f"已选择 {len(file_paths)} 个文件")
            
            # 切换到辅助标签
            self.switch_to_tab("辅助")
            
            # 切换到文件校验标签页
            if hasattr(self, 'tools_tab_widget'):
                for i in range(self.tools_tab_widget.count()):
                    if self.tools_tab_widget.tabText(i) == "文件校验":
                        self.tools_tab_widget.setCurrentIndex(i)
                        break
    
    def _discover_p2p_devices(self):
        """
        发现P2P设备
        """
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtGui import QColor
        
        try:
            # 检查P2P服务是否启用
            if not p2p_service.enabled:
                self.connection_status_label.setText("P2P服务未启用")  # pyright: ignore[reportOptionalMemberAccess]
                self.connection_status_label.setStyleSheet("font-size: 14px; color: gray;")  # pyright: ignore[reportOptionalMemberAccess]
                return
            
            # 清空设备列表
            self.device_list.clear()  # pyright: ignore[reportOptionalMemberAccess]
            
            # 发现设备
            devices = p2p_service.discover_devices()
            
            # 添加设备到列表
            for device in (devices or []):
                item = QListWidgetItem()
                item.setText(f"● {device.hostname} ({device.ip_address}:{device.port})")
                
                # 检查是否为当前设备
                is_current_device = False
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    current_ip = s.getsockname()[0]
                    s.close()
                    current_port = p2p_service._discovery.DEFAULT_BROADCAST_PORT
                    if device.ip_address == current_ip and device.port == current_port:
                        is_current_device = True
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                # 设置设备状态
                if is_current_device:
                    # 当前设备显示蓝色
                    item.setForeground(QColor(0, 0, 255))
                    item.setToolTip("当前设备")
                elif self.p2p_current_connection and hasattr(self.p2p_current_connection, 'ip_address') and self.p2p_current_connection.ip_address == device.ip_address and self.p2p_current_connection.port == device.port:
                    # 已连接设备显示绿色
                    item.setForeground(QColor(0, 128, 0))
                    item.setToolTip("已连接")
                else:
                    # 未连接设备显示红色
                    item.setForeground(QColor(255, 0, 0))
                    item.setToolTip("未连接")
                
                item.setData(Qt.ItemDataRole.UserRole, device)
                self.device_list.addItem(item)  # pyright: ignore[reportOptionalMemberAccess]
            
            try:
                self.device_list.itemClicked.disconnect(self._on_device_selected)  # pyright: ignore[reportOptionalMemberAccess]
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            self.device_list.itemClicked.connect(self._on_device_selected)  # pyright: ignore[reportOptionalMemberAccess]
            
        except Exception as e:
            logger.error(f"发现设备失败: {e}")
    
    def _on_device_selected(self, item):
        """
        设备被选择时的处理
        """
        self.selected_device = item.data(Qt.ItemDataRole.UserRole)
        
        # 启用/禁用连接按钮
        if self.selected_device:
            self.connect_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            if self.p2p_current_connection and hasattr(self.p2p_current_connection, 'ip_address') and self.p2p_current_connection.ip_address == self.selected_device.ip_address:
                self.connect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
                self.disconnect_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            else:
                self.disconnect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
        else:
            self.connect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.disconnect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _request_p2p_connection(self):
        """
        请求P2P连接
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.selected_device:
            QMessageBox.warning(self, "警告", "请先选择目标设备")
            return
        
        try:
            # 更新状态为连接中
            self.connection_status_label.setText("连接中...")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: orange;")  # pyright: ignore[reportOptionalMemberAccess]
            
            # 发送连接请求（连接是异步的，结果通过信号通知）
            p2p_service.connect(self.selected_device)
            
            self.p2p_current_connection = self.selected_device
            self.connection_status_label.setText("连接中...")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: orange;")  # pyright: ignore[reportOptionalMemberAccess]
            
            QMessageBox.information(self, "提示", f"正在连接到 {self.selected_device.hostname}，请等待连接结果")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接失败: {str(e)}")
            self.connection_status_label.setText("未连接")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: red;")  # pyright: ignore[reportOptionalMemberAccess]
    
    def _disconnect_p2p_connection(self):
        """
        断开P2P连接
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.p2p_current_connection:
            return
        
        try:
            # 断开连接
            p2p_service.disconnect(self.p2p_current_connection.device_id)
            
            # 更新状态
            self.p2p_current_connection = None
            self.connection_status = False
            self.connection_status_label.setText("未连接")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_status_label.setStyleSheet("font-size: 14px; color: red;")  # pyright: ignore[reportOptionalMemberAccess]
            self.connection_info_label.setText("")  # pyright: ignore[reportOptionalMemberAccess]
            self.current_connection_label.setText("未连接到任何设备")  # pyright: ignore[reportOptionalMemberAccess]
            self.current_connection_label.setStyleSheet("")  # pyright: ignore[reportOptionalMemberAccess]
            
            # 禁用发送文件按钮
            self.send_file_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            self.connect_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
            self.disconnect_btn.setEnabled(False)  # pyright: ignore[reportOptionalMemberAccess]
            
            # 重新扫描设备
            self._discover_p2p_devices()
            
            QMessageBox.information(self, "成功", "已断开连接")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"断开连接失败: {str(e)}")
    
    def _browse_p2p_file(self):
        """
        浏览要发送的文件
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        if not self.p2p_current_connection:
            QMessageBox.warning(self, "警告", "请先连接到目标设备")
            return
        
        # 选择文件
        files, _ = QFileDialog.getOpenFileNames(self, "选择要发送的文件", ".")
        
        if not files:
            return
        
        self.current_p2p_files = files
        
        # 开始传输
        self._start_p2p_transfer()
    
    def _start_p2p_transfer(self):
        """
        开始P2P传输
        """
        from PySide6.QtWidgets import QMessageBox
        import os
        
        if not self.p2p_current_connection:
            QMessageBox.warning(self, "警告", "请先连接到目标设备")
            return
        
        if not self.current_p2p_files:
            QMessageBox.warning(self, "警告", "请先选择要发送的文件")
            return
        
        try:
            for file_path in self.current_p2p_files:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "警告", f"文件不存在: {file_path}")
                    continue
                
                # 开始传输
                # 获取设备对象
                if isinstance(self.p2p_current_connection, dict):
                    device = self.p2p_current_connection.get("device")
                else:
                    device = self.p2p_current_connection
                
                target_path = os.path.basename(file_path)
                task_id = p2p_service.send_file(file_path, target_path)
                
                QMessageBox.information(self, "成功", f"传输通知已发送，等待对方接受，任务ID: {task_id}")
                self._refresh_p2p_tasks()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始传输失败: {str(e)}")
    
    def _refresh_p2p_tasks(self):
        """
        刷新P2P任务列表
        """
        from PySide6.QtWidgets import QTableWidgetItem, QPushButton
        
        # 检查P2P服务是否启用
        if not p2p_service.enabled:
            return
        
        # 清空任务表
        self.p2p_task_table.setRowCount(0)  # pyright: ignore[reportOptionalMemberAccess]
        
        try:
            # 获取所有P2P任务
            tasks = p2p_service.get_active_transfers()
            
            # 添加任务到表格
            for task in tasks:
                row = self.p2p_task_table.rowCount()  # pyright: ignore[reportOptionalMemberAccess]
                self.p2p_task_table.insertRow(row)  # pyright: ignore[reportOptionalMemberAccess]
                
                # 方向
                direction = "发送" if task.direction == "upload" else "接收"  # pyright: ignore[reportAttributeAccessIssue]
                self.p2p_task_table.setItem(row, 0, QTableWidgetItem(direction))  # pyright: ignore[reportOptionalMemberAccess]
                
                # 文件名
                filename = os.path.basename(task.file_path)  # pyright: ignore[reportAttributeAccessIssue]
                self.p2p_task_table.setItem(row, 1, QTableWidgetItem(filename))  # pyright: ignore[reportOptionalMemberAccess]
                
                # 进度
                progress = int((task.progress / task.total_size) * 100) if task.total_size > 0 else 0  # pyright: ignore[reportAttributeAccessIssue]
                self.p2p_task_table.setItem(row, 2, QTableWidgetItem(f"{progress}%"))  # pyright: ignore[reportOptionalMemberAccess]
                
                # 速度
                speed = task.speed / 1024 / 1024 if hasattr(task, 'speed') else 0  # pyright: ignore[reportAttributeAccessIssue]
                self.p2p_task_table.setItem(row, 3, QTableWidgetItem(f"{speed:.2f} MB/s"))  # pyright: ignore[reportOptionalMemberAccess]
                
                # 剩余时间
                if speed > 0 and task.total_size > task.progress:  # pyright: ignore[reportAttributeAccessIssue]
                    remaining = (task.total_size - task.progress) / (speed * 1024 * 1024)  # pyright: ignore[reportAttributeAccessIssue]
                    if remaining > 60:
                        remaining_text = f"{remaining / 60:.1f} 分钟"
                    else:
                        remaining_text = f"{remaining:.0f} 秒"
                else:
                    remaining_text = ""
                self.p2p_task_table.setItem(row, 4, QTableWidgetItem(remaining_text))  # pyright: ignore[reportOptionalMemberAccess]
                
                # 操作按钮
                view_btn = QPushButton("查看详情")
                view_btn.clicked.connect(lambda checked, t=task: self._view_task_detail(t))
                self.p2p_task_table.setCellWidget(row, 5, view_btn)  # pyright: ignore[reportOptionalMemberAccess]
        except Exception as e:
            logger.error(f"刷新任务列表失败: {e}")
    
    def _view_task_detail(self, task):
        """
        查看任务详情
        """
        # 显示任务详情面板
        self.task_detail_group.setVisible(True)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 计算进度百分比
        progress = int((task.progress / task.total_size) * 100) if task.total_size > 0 else 0
        
        # 计算速度
        speed = task.speed / 1024 / 1024 if hasattr(task, 'speed') else 0
        
        # 计算剩余时间
        if speed > 0 and task.total_size > task.progress:
            remaining = (task.total_size - task.progress) / (speed * 1024 * 1024)
            if remaining > 60:
                remaining_text = f"约 {remaining / 60:.1f} 分钟"
            else:
                remaining_text = f"约 {remaining:.0f} 秒"
        else:
            remaining_text = ""
        
        # 构建任务详情信息
        detail_info = f"任务详情：[{"发送" if task.direction == "upload" else "接收"}] {os.path.basename(task.file_path)}"
        detail_info += f"\n├─ 总体进度：{'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%"
        detail_info += f"\n├─ 传输速度：当前 {speed:.2f} MB/s"
        detail_info += f"\n├─ 已传输：{task.progress / 1024 / 1024:.2f} MB / {task.total_size / 1024 / 1024:.2f} MB"
        detail_info += f"\n├─ 剩余时间：{remaining_text}"
        detail_info += f"\n├─ 开始时间：{task.start_time}"
        detail_info += f"\n├─ 文件校验：MD5校验中..."
        
        self.task_detail_info.setText(detail_info)  # pyright: ignore[reportOptionalMemberAccess]
        
        # 保存当前任务
        self.current_task = task
        
        # 启用控制按钮
        self.p2p_pause_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
        self.p2p_resume_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
        self.p2p_cancel_btn.setEnabled(True)  # pyright: ignore[reportOptionalMemberAccess]
    
    def _pause_p2p_transfer(self):
        """
        暂停P2P传输
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.current_task:
            QMessageBox.warning(self, "警告", "请先选择要暂停的任务")
            return
        
        try:
            p2p_service.pause_transfer(self.current_task.task_id)
            QMessageBox.information(self, "成功", "传输任务已暂停")
            self._refresh_p2p_tasks()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"暂停传输失败: {str(e)}")
    
    def _resume_p2p_transfer(self):
        """
        恢复P2P传输
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.current_task:
            QMessageBox.warning(self, "警告", "请先选择要恢复的任务")
            return
        
        try:
            p2p_service.resume_transfer(self.current_task.task_id)
            QMessageBox.information(self, "成功", "传输任务已恢复")
            self._refresh_p2p_tasks()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复传输失败: {str(e)}")
    
    def _cancel_p2p_transfer(self):
        """
        取消P2P传输
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.current_task:
            QMessageBox.warning(self, "警告", "请先选择要取消的任务")
            return
        
        # 确认取消
        reply = QMessageBox.question(
            self, "确认", "确定要取消当前传输任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                p2p_service.cancel_transfer(self.current_task.task_id)
                QMessageBox.information(self, "成功", "传输任务已取消")
                self._refresh_p2p_tasks()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"取消传输失败: {str(e)}")
    
    def _open_receive_settings(self):
        """
        打开接收设置
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("接收设置")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 默认保存路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("默认保存路径:"))
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(os.path.join(os.path.expanduser("~"), "Downloads"))
        path_layout.addWidget(self.save_path_edit)
        
        browse_btn = QPushButton("浏览...")
        def browse_save_path():
            directory = QFileDialog.getExistingDirectory(self, "选择默认保存路径", ".")
            if directory:
                self.save_path_edit.setText(directory)
        browse_btn.clicked.connect(browse_save_path)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(lambda: self._save_receive_settings(dialog))
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _save_receive_settings(self, dialog):
        """
        保存接收设置
        """
        from PySide6.QtWidgets import QMessageBox
        
        save_path = self.save_path_edit.text().strip()
        if not save_path:
            QMessageBox.warning(self, "警告", "请输入默认保存路径")
            return
        
        try:
            logger.info(f"接收保存路径已设置: {save_path}")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
    
    def _view_transfer_history(self):
        """
        查看传输历史
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit
        from PySide6.QtCore import Qt
        from datetime import datetime
        
        # 创建历史查看对话框
        history_dialog = QDialog(self)
        history_dialog.setWindowTitle("传输历史")
        history_dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(history_dialog)
        
        # 创建文本编辑框
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        
        # 获取传输历史
        history = []
        
        if not history:
            history_text.setText("暂无传输历史")
        else:
            history_content = []
            for log in history:
                timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                action = log["action"]
                filename = log["filename"]
                device = log["device"]
                status = log["status"]
                speed = log["speed"]
                
                action_map = {
                    "started": "开始传输",
                    "completed": "传输完成",
                    "failed": "传输失败",
                    "cancelled": "取消传输"
                }
                action_text = action_map.get(action, action)
                
                log_line = f"[{timestamp}] {action_text} | 文件: {filename} | 设备: {device} | 状态: {status}"
                if speed > 0:
                    log_line += f" | 速度: {speed / 1024 / 1024:.2f} MB/s"
                history_content.append(log_line)
            
            history_text.setText("\n".join(history_content))
        
        layout.addWidget(history_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("清空历史")
        clear_btn.clicked.connect(lambda: self._clear_transfer_history(history_text))
        button_layout.addWidget(clear_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(history_dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        history_dialog.exec()
    
    def _clear_transfer_history(self, history_text):
        """
        清空传输历史
        """
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有传输历史吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("传输历史已清空")
            history_text.setText("暂无传输历史")
    
    def _on_transfer_request(self, task_id, filename, filesize, hostname, ip, address, cancel=False):
        """
        接收到传输请求的回调函数
        
        Args:
            task_id: 任务ID
            filename: 文件名
            filesize: 文件大小
            hostname: 发送方主机名
            ip: 发送方IP
            address: 地址信息
            cancel: 是否取消
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QFileDialog
        from PySide6.QtCore import Qt, QCoreApplication, QThread, QTimer
        
        # 确保在主线程中执行
        if not QCoreApplication.instance().thread() == QThread.currentThread():  # pyright: ignore[reportOptionalMemberAccess]
            QTimer.singleShot(0, lambda: self._on_transfer_request(task_id, filename, filesize, hostname, ip, address, cancel))
            return
        
        if cancel:
            # 取消对话框
            if self.transfer_request_dialog:
                try:
                    self.transfer_request_dialog.reject()
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                self.transfer_request_dialog = None
            return
        
        # 关闭已存在的对话框
        if self.transfer_request_dialog:
            try:
                self.transfer_request_dialog.reject()
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            self.transfer_request_dialog = None
        
        # 创建传输请求对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("传输请求")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # 显示传输信息
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"<b>发送方:</b> {hostname} ({ip})"))
        info_layout.addWidget(QLabel(f"<b>文件名:</b> {filename}"))
        
        # 格式化文件大小
        if filesize >= 1024 * 1024:
            size_str = f"{filesize / (1024 * 1024):.2f} MB"
        elif filesize >= 1024:
            size_str = f"{filesize / 1024:.2f} KB"
        else:
            size_str = f"{filesize} bytes"
        info_layout.addWidget(QLabel(f"<b>文件大小:</b> {size_str}"))
        info_layout.addSpacing(10)
        layout.addLayout(info_layout)
        
        # 保存路径选择
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        save_path_edit = QLineEdit()
        save_path_edit.setText(os.path.join(os.path.expanduser("~"), "Downloads", os.path.basename(filename)))
        save_path_edit.setMinimumWidth(300)
        path_layout.addWidget(save_path_edit)
        
        browse_btn = QPushButton("浏览...")
        def browse_save_path():
            file_path, _ = QFileDialog.getSaveFileName(
                dialog,
                "选择保存位置",
                save_path_edit.text()
            )
            if file_path:
                save_path_edit.setText(file_path)
        browse_btn.clicked.connect(browse_save_path)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)
        layout.addSpacing(10)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reject_btn = QPushButton("拒绝")
        def on_reject():
            try:
                # 发送拒绝消息
                p2p_service.cancel_transfer(task_id)
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            dialog.reject()
            self.transfer_request_dialog = None
        reject_btn.clicked.connect(on_reject)
        
        accept_btn = QPushButton("接收")
        accept_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        def on_accept():
            save_path = save_path_edit.text().strip()
            if not save_path:
                QMessageBox.warning(dialog, "警告", "请输入保存路径")
                return
            
            try:
                # 确认保存路径
                p2p_service.resume_transfer(task_id)
                dialog.accept()
                self.transfer_request_dialog = None
                QMessageBox.information(self, "成功", "已确认保存路径，等待发送方开始传输")
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"确认路径失败: {str(e)}")
        accept_btn.clicked.connect(on_accept)
        
        button_layout.addWidget(reject_btn)
        button_layout.addWidget(accept_btn)
        layout.addLayout(button_layout)
        
        self.transfer_request_dialog = dialog
        dialog.exec()
    
    def _update_device_list(self, devices):
        """
        更新设备列表
        """
        self._discover_p2p_devices()

    # ==== 文件合并功能 ====

    def _setup_file_merge_tab(self, tab: QWidget):
        """
        设置文件合并选项卡
        """
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 提示标签
        hint_label = QLabel("选择要合并的文本文件，按顺序合并后输出")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 文件选择区域
        file_layout = QHBoxLayout()
        self.merge_files_label = QLabel("已选择: 0 个文件")
        self.merge_files_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        file_layout.addWidget(self.merge_files_label)
        file_layout.addStretch()
        browse_merge_btn = QPushButton("选择文件")
        browse_merge_btn.setFixedWidth(80)
        browse_merge_btn.clicked.connect(self._browse_merge_files)  # pyright: ignore[reportAttributeAccessIssue]
        file_layout.addWidget(browse_merge_btn)

        from_btn = QPushButton("从面板")
        from_btn.setFixedWidth(60)
        from_btn.clicked.connect(self._add_merge_from_panel)
        file_layout.addWidget(from_btn)
        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(40)
        clear_btn.clicked.connect(lambda: self.add_files_to_merge([]))
        file_layout.addWidget(clear_btn)
        layout.addLayout(file_layout)

        # 输出路径
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("输出文件:"))
        self.merge_output_edit = QLineEdit()
        self.merge_output_edit.setPlaceholderText("合并后的文件保存路径...")
        out_layout.addWidget(self.merge_output_edit)
        browse_out_btn = QPushButton("浏览")
        browse_out_btn.setFixedWidth(50)
        browse_out_btn.clicked.connect(self._browse_merge_output)
        out_layout.addWidget(browse_out_btn)
        layout.addLayout(out_layout)

        # 选项
        option_layout = QHBoxLayout()
        self.merge_insert_title_check = QCheckBox("在每个文件内容前插入文件名标题")
        self.merge_insert_title_check.setStyleSheet("font-size: 11px;")
        option_layout.addWidget(self.merge_insert_title_check)
        self.merge_insert_blank_check = QCheckBox("文件之间插入空行分隔")
        self.merge_insert_blank_check.setStyleSheet("font-size: 11px;")
        self.merge_insert_blank_check.setChecked(True)
        option_layout.addWidget(self.merge_insert_blank_check)
        option_layout.addStretch()
        layout.addLayout(option_layout)

        # 预览
        layout.addWidget(QLabel("预览:"))
        self.merge_preview_text = QTextEdit()
        self.merge_preview_text.setReadOnly(True)
        self.merge_preview_text.setMaximumHeight(150)
        self.merge_preview_text.setStyleSheet("font-family: 'Consolas', 'Noto Sans Mono', monospace; font-size: 11px;")
        layout.addWidget(self.merge_preview_text)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        execute_btn = QPushButton("执行合并")
        execute_btn.setFixedWidth(100)
        execute_btn.clicked.connect(self._execute_merge)  # pyright: ignore[reportAttributeAccessIssue]
        btn_layout.addWidget(execute_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _browse_merge_files(self):
        """
        浏览选择要合并的文件
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要合并的文件",
            "",
            "文本文件 (*.txt *.log *.csv *.md *.py *.json *.xml *.yaml *.yml *.html *.css *.js);;所有文件 (*.*)"
        )
        if files:
            self.add_files_to_merge(files)

    def _browse_merge_output(self):
        """
        浏览选择合并输出文件路径
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存合并文件",
            "",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            self.merge_output_edit.setText(file_path)

    def _add_merge_from_panel(self):
        """
        从当前文件面板中添加选中的文件到合并列表
        """
        try:
            # FunctionPanel 的父组件是 QSplitter，需要往上找到 DualPane
            # QSplitter -> DualPane
            splitter = self.parent()
            if not splitter:
                QMessageBox.warning(self, "提示", "无法获取文件面板")
                return
            dual_pane = splitter.parent()
            logger.info(f"[合并-从面板] dual_pane type: {type(dual_pane).__name__}")
            if not dual_pane:
                QMessageBox.warning(self, "提示", "无法获取主窗口")
                return

            # 获取当前活跃的面板
            active_side = getattr(dual_pane, 'last_focused_pane', 'left')
            logger.info(f"[合并-从面板] active_side={active_side}")
            pane = getattr(dual_pane, f'{active_side}_pane', None)
            if pane is None:
                logger.warning(f"[合并-从面板] 未找到 {active_side}_pane 属性")
                QMessageBox.warning(self, "提示", f"无法获取{active_side}侧文件面板")
                return

            current_path = pane.get_current_path()
            logger.info(f"[合并-从面板] current_path={current_path}")
            if not current_path:
                logger.warning(f"[合并-从面板] 当前路径为空")
                QMessageBox.warning(self, "提示", "当前文件面板路径为空，请先导航到目标目录")
                return

            files, _ = QFileDialog.getOpenFileNames(
                self,
                "选择要合并的文件",
                current_path,
                "文本文件 (*.txt *.log *.csv *.md *.py *.json *.xml *.yaml *.yml *.html *.css *.js);;所有文件 (*.*)"
            )
            if files:
                self.add_files_to_merge(files)
        except Exception as e:
            logger.exception(f"[合并-从面板] 出错: {e}")
            QMessageBox.warning(self, "错误", f"从面板添加文件失败: {e}")

    def add_files_to_merge(self, files: list[str]):
        """
        添加文件到合并列表
        """
        if not files:
            self.merge_files = []
            self.merge_files_label.setText(f"已选择: 0 个文件")
            self._update_merge_preview()
            return
        existing = list(self.merge_files) if self.merge_files else []
        for f in files:
            if f not in existing:
                existing.append(f)
        self.merge_files = existing
        self.merge_files_label.setText(f"已选择: {len(self.merge_files)} 个文件")
        self._update_merge_preview()

    def _update_merge_preview(self):
        """
        更新合并预览（自然排序）
        """
        self.merge_preview_text.clear()
        if not self.merge_files:
            return
        try:
            ordered = sorted(self.merge_files, key=tools_service.file_merger.natural_sort_key)
        except Exception:
            ordered = sorted(self.merge_files, key=lambda p: os.path.basename(p).lower())
        preview_lines = []
        for i, f in enumerate(ordered):
            if i >= 5:
                preview_lines.append(f"  ... 还有 {len(ordered) - 5} 个文件")
                break
            preview_lines.append(f"  {i+1}. {os.path.basename(f)}")
        self.merge_preview_text.setPlainText("\n".join(preview_lines))

    def _execute_merge(self):
        """
        执行文件合并
        """
        if not self.merge_files:
            QMessageBox.warning(self, "提示", "请先选择要合并的文件")
            return

        output_path = self.merge_output_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "提示", "请指定输出文件路径")
            return

        insert_title = self.merge_insert_title_check.isChecked()
        insert_blank = self.merge_insert_blank_check.isChecked()

        sorted_files = sorted(self.merge_files, key=tools_service.file_merger.natural_sort_key)
        file_count = len(sorted_files)
        logger.info(f"[文件合并] 开始合并 {file_count} 个文件 -> {output_path}")

        def on_progress(current, total, filename):
            self.merge_preview_text.setPlainText(
                f"正在合并 ({current}/{total}): {filename}"
            )
            QApplication.processEvents()

        try:
            result = tools_service.merge_files(
                self.merge_files, output_path, insert_title, insert_blank,
                progress_callback=on_progress)

            if result.get("success"):
                count = result.get("count", 0)
                total_size = result.get("total_size", 0)
                size_str = f"{total_size / 1024:.1f} KB" if total_size > 1024 else f"{total_size} B"
                msg = result.get("message", "合并完成")
                logger.info(f"[文件合并] 完成: {count} 个文件, 总大小 {size_str}")

                preview_lines = []
                for i, f in enumerate(sorted_files):
                    preview_lines.append(f"  {i+1}. {os.path.basename(f)}")
                preview_lines.append("")
                preview_lines.append(f"合并完成: {count} 个文件, 总大小 {size_str}")
                preview_lines.append(f"输出: {output_path}")
                self.merge_preview_text.setPlainText("\n".join(preview_lines))

                QMessageBox.information(
                    self,
                    "合并完成",
                    f"{msg}\n\n文件数: {count}\n总大小: {size_str}\n输出: {output_path}"
                )
            else:
                err_msg = result.get("message", "未知错误")
                logger.warning(f"[文件合并] 失败: {err_msg}")
                self.merge_preview_text.setPlainText(f"合并失败:\n{err_msg}")
                QMessageBox.warning(self, "合并失败", err_msg)
        except Exception as e:
            logger.exception(f"[文件合并] 异常: {e}")
            self.merge_preview_text.setPlainText(f"合并出错:\n{str(e)}")
            QMessageBox.critical(self, "合并失败", f"合并文件时出错:\n{str(e)}")


class SearchResultDialog(QDialog):
    """
    搜索结果对话框
    用于显示所有搜索结果
    """
    
    def __init__(self, results, search_info=None, parent=None):
        """
        初始化搜索结果对话框
        
        Args:
            results: 搜索结果列表
            search_info: 搜索条件信息
            parent: 父组件
        """
        super().__init__(parent)
        self.results = results
        self.search_info = search_info or {}
        # UI组件引用（在init_ui中设置）
        self.tools_tab = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.tools_tab_widget = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_type_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.prefix_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.suffix_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.old_text_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.new_text_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.start_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.padding_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_preview = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.rename_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.target_encoding_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.backup_checkbox = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_preview = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.encoding_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.target_format_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.quality_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.overwrite_checkbox = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_info_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.image_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.hash_algo_combo = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_result_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.verify_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_files_label = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_output_edit = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_insert_title_check = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_insert_blank_check = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_preview_text = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.merge_files = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.init_ui()
        self.populate_results()
    
    def init_ui(self):
        """
        初始化搜索结果对话框UI组件
        """
        # 设置对话框标题和大小
        self.setWindowTitle("搜索结果")
        self.setMinimumSize(800, 600)
        # 显示最大化和最小化按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建结果数量标签
        search_method = self.search_info.get('search_method', 'traditional')
        method_text = "（快速搜索）" if search_method == 'unified_fast_search' else ""
        self.results_count_label = QLabel(f"找到 {len(self.results)} 个结果{method_text}")
        main_layout.addWidget(self.results_count_label)
        
        # 创建结果表格视图
        self.result_table = QTableView()
        
        # 创建结果模型
        self.result_model = QStandardItemModel()
        self.result_model.setHorizontalHeaderLabels(["名称", "路径", "大小", "修改日期", "编码"])
        
        # 设置模型到表格视图
        self.result_table.setModel(self.result_model)
        
        # 设置表格属性
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(True)
        
        # 对于前4列，使用ResizeToContents模式，根据内容自适应宽度
        for i in range(4):
            self.result_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # 对于最后一列（编码），使用Stretch模式，填充剩余空间
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 允许用户手动调整所有列宽
        self.result_table.horizontalHeader().setSectionsMovable(True)
        
        # 连接双击事件
        self.result_table.doubleClicked.connect(self._on_double_click)
        
        # 连接右键菜单事件
        self.result_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_table.customContextMenuRequested.connect(self._show_context_menu)
        
        # 添加表格到布局
        main_layout.addWidget(self.result_table)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建打开按钮
        open_btn = QPushButton("打开")
        open_btn.clicked.connect(self._on_open_clicked)
        button_layout.addWidget(open_btn)
        
        # 创建打开所在目录按钮
        open_dir_btn = QPushButton("打开所在目录")
        open_dir_btn.clicked.connect(self._on_open_dir_clicked)
        button_layout.addWidget(open_dir_btn)
        
        # 添加导出HTML按钮
        export_btn = QPushButton("导出HTML")
        export_btn.clicked.connect(self._export_to_html)
        button_layout.addWidget(export_btn)
        
        # 创建关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        # 添加按钮布局到主布局
        main_layout.addLayout(button_layout)
    
    def _setup_tools_panel(self):
        """
        设置辅助工具面板的UI组件和布局
        """
        from PySide6.QtWidgets import (QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, 
                                    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
                                    QFormLayout, QGroupBox, QTabWidget, QTextEdit, QProgressBar)
        from PySide6.QtCore import Qt
        
        # 创建辅助工具面板布局
        tools_layout = QVBoxLayout(self.tools_tab)  # pyright: ignore[reportAttributeAccessIssue, reportArgumentType]
        
        # 创建工具标签页
        self.tools_tab_widget = QTabWidget()
        
        # 批量重命名标签页
        rename_tab = QWidget()
        self._setup_batch_rename_tab(rename_tab)
        self.tools_tab_widget.addTab(rename_tab, "批量重命名")
        
        # 文件编码转换标签页
        encoding_tab = QWidget()
        self._setup_encoding_convert_tab(encoding_tab)
        self.tools_tab_widget.addTab(encoding_tab, "编码转换")
        
        # 图片格式转换标签页
        image_tab = QWidget()
        self._setup_image_convert_tab(image_tab)
        self.tools_tab_widget.addTab(image_tab, "图片转换")
        
        # 文件校验标签页
        verify_tab = QWidget()
        self._setup_file_verify_tab(verify_tab)
        self.tools_tab_widget.addTab(verify_tab, "文件校验")
        
        # 文件合并标签页
        merge_tab = QWidget()
        self._setup_file_merge_tab(merge_tab)  # pyright: ignore[reportAttributeAccessIssue]
        self.tools_tab_widget.addTab(merge_tab, "文件合并")
        
        tools_layout.addWidget(self.tools_tab_widget)
    
    def _setup_batch_rename_tab(self, parent):
        """
        设置批量重命名标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.rename_files_label = QLabel("未选择文件")
        self.rename_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.rename_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_rename_files)
        file_layout.addWidget(self.rename_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 重命名规则区域
        rule_group = QGroupBox("重命名规则")
        rule_layout = QFormLayout(rule_group)
        
        self.rename_type_combo = QComboBox()
        self.rename_type_combo.addItems(["添加前缀", "添加后缀", "替换文本", "添加序号"])
        rule_layout.addRow("重命名类型:", self.rename_type_combo)
        
        # 前缀设置
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("输入前缀")
        rule_layout.addRow("前缀:", self.prefix_edit)
        
        # 后缀设置
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("输入后缀")
        rule_layout.addRow("后缀:", self.suffix_edit)
        
        # 替换文本设置
        self.old_text_edit = QLineEdit()
        self.old_text_edit.setPlaceholderText("输入要替换的文本")
        rule_layout.addRow("旧文本:", self.old_text_edit)
        
        self.new_text_edit = QLineEdit()
        self.new_text_edit.setPlaceholderText("输入新文本")
        rule_layout.addRow("新文本:", self.new_text_edit)
        
        # 序号设置
        self.start_edit = QLineEdit("1")
        rule_layout.addRow("起始序号:", self.start_edit)  # pyright: ignore[reportArgumentType]
        
        self.padding_edit = QLineEdit("3")
        rule_layout.addRow("序号填充:", self.padding_edit)  # pyright: ignore[reportArgumentType]
        
        layout.addWidget(rule_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.rename_preview = QTextEdit()
        self.rename_preview.setReadOnly(True)
        preview_layout.addWidget(self.rename_preview)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self._preview_rename)
        execute_btn = QPushButton("执行")
        execute_btn.clicked.connect(self._execute_rename)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(execute_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.rename_files = []
    
    def _browse_rename_files(self):
        """
        选择要重命名的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.rename_files = files
            self.rename_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _preview_rename(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        预览重命名结果
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.rename_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            rename_type = self.rename_type_combo.currentText()
            
            if rename_type == "添加前缀":
                prefix = self.prefix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "prefix", prefix=prefix)
            elif rename_type == "添加后缀":
                suffix = self.suffix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "suffix", suffix=suffix)
            elif rename_type == "替换文本":
                old_text = self.old_text_edit.text().strip()
                new_text = self.new_text_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "replace", old_text=old_text, new_text=new_text)
            elif rename_type == "添加序号":
                start = int(self.start_edit.text().strip() or "1")
                padding = int(self.padding_edit.text().strip() or "3")
                rename_map = tools_service.batch_rename(self.rename_files, "serial", start=start, padding=padding)
            else:
                QMessageBox.warning(self, "警告", "不支持的重命名类型")
                return
            
            # 显示预览结果
            preview_text = "重命名预览:\n\n"
            for old_path, new_path in rename_map.items():
                preview_text += f"{os.path.basename(old_path)} → {os.path.basename(new_path)}\n"
            
            self.rename_preview.setText(preview_text)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览失败: {str(e)}")
    
    def _execute_rename(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行批量重命名
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.rename_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            rename_type = self.rename_type_combo.currentText()
            
            if rename_type == "添加前缀":
                prefix = self.prefix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "prefix", prefix=prefix)
            elif rename_type == "添加后缀":
                suffix = self.suffix_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "suffix", suffix=suffix)
            elif rename_type == "替换文本":
                old_text = self.old_text_edit.text().strip()
                new_text = self.new_text_edit.text().strip()
                rename_map = tools_service.batch_rename(self.rename_files, "replace", old_text=old_text, new_text=new_text)
            elif rename_type == "添加序号":
                start = int(self.start_edit.text().strip() or "1")
                padding = int(self.padding_edit.text().strip() or "3")
                rename_map = tools_service.batch_rename(self.rename_files, "serial", start=start, padding=padding)
            else:
                QMessageBox.warning(self, "警告", "不支持的重命名类型")
                return
            
            # 执行重命名
            failed = tools_service.execute_rename(rename_map)
            
            if failed:
                QMessageBox.warning(self, "警告", f"部分文件重命名失败: {len(failed)} 个文件")
            else:
                QMessageBox.information(self, "成功", f"成功重命名 {len(rename_map)} 个文件")
                self.rename_files = []
                self.rename_files_label.setText("未选择文件")
                self.rename_preview.clear()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行失败: {str(e)}")
    
    def _setup_encoding_convert_tab(self, parent):
        """
        设置文件编码转换标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.encoding_files_label = QLabel("未选择文件")
        self.encoding_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.encoding_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_encoding_files)
        file_layout.addWidget(self.encoding_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 编码设置区域
        encode_layout = QFormLayout()
        self.target_encoding_combo = QComboBox()
        self.target_encoding_combo.addItems(["utf-8", "gbk", "ascii", "utf-16", "utf-32"])
        encode_layout.addRow("目标编码:", self.target_encoding_combo)
        
        self.backup_checkbox = QCheckBox("备份原文件")
        self.backup_checkbox.setChecked(True)
        encode_layout.addRow(self.backup_checkbox)
        layout.addLayout(encode_layout)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.encoding_preview = QTextEdit()
        self.encoding_preview.setReadOnly(True)
        preview_layout.addWidget(self.encoding_preview)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        detect_btn = QPushButton("检测编码")
        detect_btn.clicked.connect(self._detect_encoding)
        convert_btn = QPushButton("转换")
        convert_btn.clicked.connect(self._execute_encoding_convert)
        btn_layout.addWidget(detect_btn)
        btn_layout.addWidget(convert_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.encoding_files = []
    
    def _browse_encoding_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要转换编码的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.encoding_files = files
            self.encoding_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _detect_encoding(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        检测文件编码
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.encoding_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            result = "文件编码检测结果:\n\n"
            for file_path in self.encoding_files:
                encoding = tools_service.detect_encoding(file_path)
                result += f"{os.path.basename(file_path)}: {encoding}\n"
            
            self.encoding_preview.setText(result)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检测编码失败: {str(e)}")
    
    def _execute_encoding_convert(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行文件编码转换
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.encoding_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            target_encoding = self.target_encoding_combo.currentText()
            backup = self.backup_checkbox.isChecked()
            
            results = tools_service.convert_encoding(self.encoding_files, target_encoding, backup)
            
            # 显示结果
            result_text = "编码转换结果:\n\n"
            for file_path, status in results.items():
                result_text += f"{os.path.basename(file_path)}: {status}\n"
            
            self.encoding_preview.setText(result_text)
            QMessageBox.information(self, "成功", "编码转换完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败: {str(e)}")
    
    def _setup_image_convert_tab(self, parent):
        """
        设置图片格式转换标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.image_files_label = QLabel("未选择文件")
        self.image_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.image_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_image_files)
        file_layout.addWidget(self.image_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 转换设置区域
        convert_layout = QFormLayout()
        self.target_format_combo = QComboBox()
        self.target_format_combo.addItems(["jpg", "png", "gif", "bmp", "webp"])
        convert_layout.addRow("目标格式:", self.target_format_combo)  # pyright: ignore[reportArgumentType]
        
        self.quality_edit = QLineEdit("85")
        convert_layout.addRow("图片质量:", self.quality_edit)
        
        self.overwrite_checkbox = QCheckBox("覆盖原文件")
        convert_layout.addRow(self.overwrite_checkbox)
        layout.addLayout(convert_layout)
        
        # 预览区域
        preview_group = QGroupBox("图片信息")
        preview_layout = QVBoxLayout(preview_group)
        
        self.image_info_text = QTextEdit()
        self.image_info_text.setReadOnly(True)
        preview_layout.addWidget(self.image_info_text)
        layout.addWidget(preview_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        info_btn = QPushButton("查看信息")
        info_btn.clicked.connect(self._show_image_info)
        convert_btn = QPushButton("转换")
        convert_btn.clicked.connect(self._execute_image_convert)
        btn_layout.addWidget(info_btn)
        btn_layout.addWidget(convert_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.image_files = []
    
    def _browse_image_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要转换的图片文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", ".", "图片文件 (*.jpg *.jpeg *.png *.gif *.bmp *.webp)")
        if files:
            self.image_files = files
            self.image_files_label.setText(f"已选择 {len(files)} 个图片")
    
    def _show_image_info(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        显示图片信息
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.image_files:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return
        
        try:
            result = "图片信息:\n\n"
            for file_path in self.image_files:
                info = tools_service.get_image_info(file_path)
                result += f"{os.path.basename(file_path)}:\n"
                for key, value in info.items():
                    result += f"  {key}: {value}\n"
                result += "\n"
            
            self.image_info_text.setText(result)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取信息失败: {str(e)}")
    
    def _execute_image_convert(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行图片格式转换
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.image_files:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return
        
        try:
            target_format = self.target_format_combo.currentText()
            quality = int(self.quality_edit.text())
            overwrite = self.overwrite_checkbox.isChecked()
            
            results = tools_service.convert_image_format(self.image_files, target_format, quality, overwrite=overwrite)
            
            # 显示结果
            result_text = "图片转换结果:\n\n"
            for file_path, status in results.items():
                result_text += f"{os.path.basename(file_path)}: {status}\n"
            
            self.image_info_text.setText(result_text)
            QMessageBox.information(self, "成功", "图片转换完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败: {str(e)}")
    
    def _setup_file_verify_tab(self, parent):
        """
        设置文件校验标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.verify_files_label = QLabel("未选择文件")
        self.verify_files_label.setStyleSheet("border: 1px solid #ddd; padding: 5px;")
        self.verify_files_label.setMinimumHeight(30)
        browse_btn = QPushButton("选择文件...")
        browse_btn.clicked.connect(self._browse_verify_files)
        file_layout.addWidget(self.verify_files_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 算法选择区域
        algo_layout = QFormLayout()
        self.hash_algo_combo = QComboBox()
        self.hash_algo_combo.addItems(["md5", "sha1", "sha256"])
        algo_layout.addRow("哈希算法:", self.hash_algo_combo)
        layout.addLayout(algo_layout)
        
        # 校验结果区域
        result_group = QGroupBox("校验结果")
        result_layout = QVBoxLayout(result_group)
        
        self.verify_result_text = QTextEdit()
        self.verify_result_text.setReadOnly(True)
        result_layout.addWidget(self.verify_result_text)
        layout.addWidget(result_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        calculate_btn = QPushButton("计算哈希")
        calculate_btn.clicked.connect(self._calculate_file_hash)
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self._export_verify_report)
        btn_layout.addWidget(calculate_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
        
        # 保存选中的文件
        self.verify_files = []
    
    def _browse_verify_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要校验的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", ".")
        if files:
            self.verify_files = files
            self.verify_files_label.setText(f"已选择 {len(files)} 个文件")
    
    def _calculate_file_hash(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        计算文件哈希值
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.verify_files:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        try:
            algorithm = self.hash_algo_combo.currentText()
            hashes = tools_service.calculate_file_hash(self.verify_files, algorithm)
            
            # 显示结果
            result_text = f"文件{algorithm.upper()}校验结果:\n\n"
            for file_path, hash_value in hashes.items():
                result_text += f"{os.path.basename(file_path)}: {hash_value}\n"
            
            self.verify_result_text.setText(result_text)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算哈希失败: {str(e)}")
    
    def _export_verify_report(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        导出校验报告
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.verify_files:
            QMessageBox.warning(self, "警告", "请先选择文件并计算哈希")
            return
        
        try:
            algorithm = self.hash_algo_combo.currentText()
            report = tools_service.generate_verification_report(self.verify_files, algorithm)
            
            # 保存报告到文件
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(self, "导出报告", f"verify_report.txt", "文本文件 (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                QMessageBox.information(self, "成功", f"报告已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def _setup_file_merge_tab(self, parent):
        """
        设置文件合并标签页
        """
        layout = QVBoxLayout(parent)
        
        # 文件选择区
        files_group = QGroupBox("待合并文件")
        files_layout = QVBoxLayout(files_group)
        
        self.merge_files_label = QLabel("尚未选择文件")
        self.merge_files_label.setWordWrap(True)
        files_layout.addWidget(self.merge_files_label)
        
        merge_files_btn = QPushButton("选择文件...")
        merge_files_btn.clicked.connect(self._browse_merge_files)
        files_layout.addWidget(merge_files_btn)
        
        # 输出文件名
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出文件名:"))
        self.merge_output_edit = QLineEdit("合并结果.md")
        output_layout.addWidget(self.merge_output_edit)
        files_layout.addLayout(output_layout)
        
        layout.addWidget(files_group)
        
        # 合并选项
        options_group = QGroupBox("合并选项")
        options_layout = QVBoxLayout(options_group)
        
        self.merge_insert_title_check = QCheckBox("在每个文件前插入文件名分隔标题")
        self.merge_insert_blank_check = QCheckBox("文件之间插入空行分隔")
        options_layout.addWidget(self.merge_insert_title_check)
        options_layout.addWidget(self.merge_insert_blank_check)
        
        layout.addWidget(options_group)
        
        # 合并按钮
        merge_btn = QPushButton("合并文件")
        merge_btn.clicked.connect(self._execute_merge)
        layout.addWidget(merge_btn)
        
        # 预览区（显示参与合并的文件顺序）
        preview_group = QGroupBox("合并顺序预览")
        preview_layout = QVBoxLayout(preview_group)
        self.merge_preview_text = QTextEdit()
        self.merge_preview_text.setReadOnly(True)
        preview_layout.addWidget(self.merge_preview_text)
        layout.addWidget(preview_group)
        
        # 保存选中的文件
        self.merge_files = []
    
    def _browse_merge_files(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        选择要合并的文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(self, "选择要合并的文件", ".")
        if files:
            self.add_files_to_merge(files)
    
    def add_files_to_merge(self, file_paths):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        将文件添加到合并列表（供外部调用，如双窗口选中文件）
        """
        if not file_paths:
            return
        existing = list(self.merge_files)  # pyright: ignore[reportArgumentType]
        for fp in file_paths:
            if fp not in existing:
                existing.append(fp)
        self.merge_files = existing
        self.merge_files_label.setText(f"已选择 {len(self.merge_files)} 个文件")
        self._update_merge_preview()
    
    def _update_merge_preview(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        更新合并顺序预览（自然排序）
        """
        try:
            ordered = sorted(self.merge_files, key=tools_service.file_merger.natural_sort_key)  # pyright: ignore[reportArgumentType, reportCallIssue]
        except Exception:
            ordered = sorted(self.merge_files, key=lambda p: os.path.basename(p).lower())  # pyright: ignore[reportArgumentType, reportCallIssue]
        preview = "\n".join(f"{i+1}. {os.path.basename(p)}" for i, p in enumerate(ordered))
        self.merge_preview_text.setText(preview)
    
    def _execute_merge(self):
        # pyright: ignore[reportOptionalMemberAccess]
        """
        执行文件合并
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not self.merge_files:
            QMessageBox.warning(self, "警告", "请先选择要合并的文件")
            return
        
        output_name = self.merge_output_edit.text().strip()
        if not output_name:
            QMessageBox.warning(self, "警告", "请输入输出文件名")
            return
        
        base_dir = os.path.dirname(self.merge_files[0])
        output_path = os.path.join(base_dir, output_name)
        
        insert_title = self.merge_insert_title_check.isChecked()
        insert_blank = self.merge_insert_blank_check.isChecked()
        
        try:
            result = tools_service.merge_files(
                self.merge_files, output_path, insert_title, insert_blank)
            if result.get("success"):
                msg = result.get("message", "合并完成")
                size = result.get("total_size", 0)
                count = result.get("count", 0)
                QMessageBox.information(
                    self, "成功",
                    f"{msg}\n\n文件数: {count}\n总大小: {format_size(size)}"
                )
            else:
                QMessageBox.warning(self, "合并失败", result.get("message", "未知错误"))  # pyright: ignore[reportArgumentType]
        except Exception as e:
            QMessageBox.critical(self, "错误", f"合并失败: {str(e)}")
    
    def _browse_search_directory(self):
        """
        浏览搜索目录
        """
        from PySide6.QtWidgets import QFileDialog
        
        directory = QFileDialog.getExistingDirectory(self, "选择搜索目录", ".")
        if directory:
            self.search_directory.setText(directory)  # pyright: ignore[reportAttributeAccessIssue]
    
    def populate_results(self):
        """
        填充搜索结果到表格中
        """
        # 清空现有结果
        self.result_model.clear()
        self.result_model.setHorizontalHeaderLabels(["名称", "路径", "大小", "修改日期", "编码"])
        
        # 添加结果到模型
        for result in self.results:
            name = result.get("name", result.get("filename", ""))
            path = result.get("path", "")
            size = result.get("size", 0)
            mtime = result.get("modified_time", result.get("mtime", None))
            
            name_item = QStandardItem(name)
            path_item = QStandardItem(path)
            size_item = QStandardItem(format_size(size) if size else "")
            
            if mtime:
                try:
                    mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mtime, 'strftime') else str(mtime)
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                    mtime_str = str(mtime)
            else:
                mtime_str = ""
            mtime_item = QStandardItem(mtime_str)
            
            # 检测文件编码
            encoding = detect_file_encoding(result["path"])
            encoding_item = QStandardItem(encoding)  # pyright: ignore[reportArgumentType, reportCallIssue]
            
            # 设置项目数据
            name_item.setData(result["path"], Qt.ItemDataRole.UserRole)
            path_item.setData(result["path"], Qt.ItemDataRole.UserRole)
            size_item.setData(result["path"], Qt.ItemDataRole.UserRole)
            mtime_item.setData(result["path"], Qt.ItemDataRole.UserRole)
            encoding_item.setData(result["path"], Qt.ItemDataRole.UserRole)
            
            # 设置文本对齐
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            mtime_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            encoding_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # 添加行到模型
            self.result_model.appendRow([name_item, path_item, size_item, mtime_item, encoding_item])
        
        # 数据填充完成后，手动调整所有列的宽度，确保路径列正确显示
        self.result_table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        # 对于最后一列（编码），使用Stretch模式，填充剩余空间
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    
    def _on_double_click(self, index):
        """
        处理双击事件
        
        Args:
            index: 双击的索引
        """
        file_path = index.data(Qt.ItemDataRole.UserRole)
        self._open_file(file_path)
    
    def _on_open_clicked(self):
        """
        处理打开按钮点击事件
        """
        selected_indexes = self.result_table.selectedIndexes()
        if selected_indexes:
            file_path = selected_indexes[0].data(Qt.ItemDataRole.UserRole)
            self._open_file(file_path)
    
    def _on_open_dir_clicked(self):
        """
        处理打开所在目录按钮点击事件
        """
        selected_indexes = self.result_table.selectedIndexes()
        if selected_indexes:
            file_path = selected_indexes[0].data(Qt.ItemDataRole.UserRole)
            dir_path = os.path.dirname(file_path)
            self._open_directory(dir_path)
    
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 右键点击的位置
        """
        # 创建菜单
        menu = QMenu(self)
        
        # 添加打开菜单项
        open_action = QAction("打开", self)
        open_action.triggered.connect(self._on_open_clicked)
        menu.addAction(open_action)
        
        # 添加预览菜单项
        preview_action = QAction("预览", self)
        preview_action.triggered.connect(self._on_preview_clicked)
        menu.addAction(preview_action)
        
        # 添加分隔符
        menu.addSeparator()
        
        # 添加打开所在目录菜单项
        open_dir_action = QAction("打开所在目录", self)
        open_dir_action.triggered.connect(self._on_open_dir_clicked)
        menu.addAction(open_dir_action)
        
        # 显示菜单
        menu.exec_(self.result_table.mapToGlobal(pos))
    
    def _open_file(self, file_path):
        """
        打开文件
        
        Args:
            file_path: 文件路径
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
            show_warning(self, "打开失败", f"无法打开文件: {e}")
    
    def _open_directory(self, dir_path):
        """
        打开目录
        
        Args:
            dir_path: 目录路径
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(dir_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', dir_path])
            logger.info(f"已打开目录: {dir_path}")
        except Exception as e:
            logger.error(f"打开目录失败: {dir_path}, 错误: {e}")
            show_warning(self, "打开失败", f"无法打开目录: {e}")
    
    def _on_preview_clicked(self):
        """
        处理预览菜单项点击
        """
        selected_indexes = self.result_table.selectedIndexes()
        if selected_indexes:
            file_path = selected_indexes[0].data(Qt.ItemDataRole.UserRole)
            self._preview_file(file_path)
    
    def _preview_file(self, file_path):
        """
        预览文件
        
        Args:
            file_path: 文件路径
        """
        # 直接使用搜索结果对话框的父窗口（即FunctionPanel）
        function_panel = self.parent()
        
        if function_panel and hasattr(function_panel, 'update_preview'):
            # 确保功能面板可见（如果function_panel是FunctionPanel实例）
            if hasattr(function_panel, 'isVisible') and not function_panel.isVisible():  # pyright: ignore[reportAttributeAccessIssue]
                # 尝试显示功能面板
                main_window = function_panel.parent()
                if main_window and hasattr(main_window, 'toggle_function_panel'):
                    main_window.toggle_function_panel()  # pyright: ignore[reportAttributeAccessIssue]
            
            # 切换到预览标签
            if hasattr(function_panel, 'switch_to_tab'):
                function_panel.switch_to_tab("预览")  # pyright: ignore[reportAttributeAccessIssue]
            
            # 更新预览内容
            function_panel.update_preview(file_path)  # pyright: ignore[reportAttributeAccessIssue]
        else:
            # 如果无法获取功能面板，直接使用预览服务
            from services.preview_service import preview_service
            preview_widget = preview_service.preview_file(file_path, self)
            
            # 显示预览内容
            dialog = QDialog(self)
            dialog.setWindowTitle(f"预览: {os.path.basename(file_path)}")
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout(dialog)
            layout.addWidget(preview_widget)
            dialog.exec()
    
    def _export_to_html(self):
        """
        导出搜索结果到HTML文件
        """
        from PySide6.QtWidgets import QFileDialog
        import datetime
        
        # 获取当前时间
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出HTML", f"搜索结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "HTML文件 (*.html)"
        )
        
        if not file_path:
            return
        
        # 确保文件具有.html扩展名
        if not file_path.lower().endswith('.html') and not file_path.lower().endswith('.htm'):
            file_path += '.html'
        
        # 生成HTML内容
        html = f"<!DOCTYPE html>\n"
        html += f"<html>\n"
        html += f"<head>\n"
        html += f"<meta charset='utf-8'>\n"
        html += f"<title>搜索结果</title>\n"
        html += f"<style>\n"
        html += f"body {{ font-family: Arial, sans-serif; margin: 20px; }}  \n"
        html += f"h1 {{ color: #333; }}  \n"
        html += f".info {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; border-radius: 5px; }}  \n"
        html += f".info p {{ margin: 5px 0; }}  \n"
        html += f"table {{ border-collapse: collapse; width: 100%; }}  \n"
        html += f"th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}  \n"
        html += f"th {{ background-color: #f2f2f2; }}  \n"
        html += f"tr:nth-child(even) {{ background-color: #f9f9f9; }}  \n"
        html += f"</style>\n"
        html += f"</head>\n"
        html += f"<body>\n"
        
        # 添加搜索条件信息（首行关键信息）
        html += f"<div class='info'>\n"
        html += f"<h1>搜索结果</h1>\n"
        html += f"<p><strong>查询关键字:</strong> {self.search_info.get('keyword', '无')}</p>\n"
        html += f"<p><strong>目录范围:</strong> {self.search_info.get('directory', '无')}</p>\n"
        html += f"<p><strong>包含子目录:</strong> {'是' if self.search_info.get('include_subdirectories', False) else '否'}</p>\n"
        html += f"<p><strong>搜索文件内容:</strong> {'是' if self.search_info.get('search_content', False) else '否'}</p>\n"
        html += f"<p><strong>文件类型:</strong> {self.search_info.get('file_type', '所有文件')}</p>\n"
        html += f"<p><strong>搜索时间:</strong> {current_time}</p>\n"
        html += f"<p><strong>结果数量:</strong> {len(self.results)}</p>\n"
        html += f"</div>\n"
        
        # 添加结果表格
        html += f"<table>\n"
        html += f"<tr>\n"
        html += f"<th>名称</th>\n"
        html += f"<th>路径</th>\n"
        html += f"<th>大小</th>\n"
        html += f"<th>修改日期</th>\n"
        html += f"<th>编码</th>\n"
        html += f"</tr>\n"
        
        # 添加结果数据
        for result in self.results:
            # 转换为file://协议格式
            result_file_path = result['path']
            # 对于Windows路径，需要特殊处理
            if os.name == 'nt':
                # 将C:\path\to\file转换为file:///C:/path/to/file
                file_url = f"file:///{result_file_path.replace('\\', '/')}"
            else:
                # 对于Linux/macOS，直接使用路径
                file_url = f"file://{result_file_path}"
            
            # 获取目录路径
            dir_path = os.path.dirname(result_file_path)
            if os.name == 'nt':
                dir_url = f"file:///{dir_path.replace('\\', '/')}"
            else:
                dir_url = f"file://{dir_path}"
            
            # 检测文件编码
            encoding = detect_file_encoding(result_file_path)
            
            html += f"<tr>\n"
            # 名称列添加链接，点击打开文件
            html += f"<td><a href='{file_url}' target='_blank'>{result['name']}</a></td>\n"
            # 路径列添加链接，点击打开目录
            html += f"<td><a href='{dir_url}' target='_blank'>{result['path']}</a></td>\n"
            html += f"<td>{format_size(result['size'])}</td>\n"
            mod_time = result.get('modified_time', result.get('mtime', None))
            mod_str = mod_time.strftime('%Y-%m-%d %H:%M:%S') if mod_time else 'N/A'
            html += f"<td>{mod_str}</td>\n"
            html += f"<td>{encoding}</td>\n"
            html += f"</tr>\n"
        
        html += f"</table>\n"
        html += f"</body>\n"
        html += f"</html>\n"
        
        # 写入文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            show_info(self, "导出成功", f"搜索结果已成功导出到: {file_path}")
        except Exception as e:
            logger.error(f"导出HTML失败: {e}")
            show_warning(self, "导出失败", f"无法导出HTML文件: {e}")


class CompareResultDialog(QDialog):
    """
    对比结果对话框
    用于显示文件对比结果和提供导出功能
    """
    
    class ImageViewer(QGraphicsView):
        """
        自定义图片查看器
        支持放大缩小、拖动和经纬参考线
        """
        # 缩放和拖动信号
        zoom_changed = Signal(float)
        pan_changed = Signal(float, float)
        
        def __init__(self, parent=None):  # pyright: ignore[reportAttributeAccessIssue]
            from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
            from PySide6.QtCore import Qt, Signal
            from PySide6.QtGui import QPen, QColor, QPainter
            
            super().__init__(parent)
            
            # 创建场景
            self._image_scene = QGraphicsScene(self)
            self.setScene(self._image_scene)
            
            # 设置属性
            self.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            # 存储图片项
            self.pixmap_item = None
            
            # 存储参考线
            self.grid_lines = []
            self.show_grid = False
            
            # 存储原始大小
            self.original_size = None
            self.last_mouse_pos = None  # pyright: ignore[reportUnannotatedClassAttribute]
            
        def setPixmap(self, pixmap):  # pyright: ignore[reportAttributeAccessIssue]
            """
            设置图片
            """
            from PySide6.QtWidgets import QGraphicsPixmapItem
            
            # 清除场景
            self._image_scene.clear()
            self.grid_lines = []
            
            # 添加图片
            if not pixmap.isNull():
                self.pixmap_item = QGraphicsPixmapItem(pixmap)
                self._image_scene.addItem(self.pixmap_item)
                self.original_size = pixmap.size()
                
                # 调整场景大小
                self._image_scene.setSceneRect(self.pixmap_item.boundingRect())
                
                # 初始缩放以适应窗口
                self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        
        def wheelEvent(self, event):
            """
            处理鼠标滚轮事件，实现缩放
            """
            from PySide6.QtCore import Qt
            
            # 获取缩放因子
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            # 计算当前缩放
            current_scale = self.transform().m11()
            
            # 处理滚轮事件
            if event.angleDelta().y() > 0:
                # 放大
                if current_scale < 10.0:  # 限制最大缩放
                    self.scale(zoom_in_factor, zoom_in_factor)
            else:
                # 缩小
                if current_scale > 0.1:  # 限制最小缩放
                    self.scale(zoom_out_factor, zoom_out_factor)
            
            # 发出缩放变化信号
            new_scale = self.transform().m11()
            self.zoom_changed.emit(new_scale)
        
        def toggleGrid(self):
            """
            显示/隐藏经纬参考线
            """
            from PySide6.QtGui import QPen, QColor
            
            # 清除现有参考线
            for line in self.grid_lines:
                self._image_scene.removeItem(line)
            self.grid_lines = []
            
            # 切换状态
            self.show_grid = not self.show_grid
            
            # 添加新参考线
            if self.show_grid and self.pixmap_item:
                rect = self.pixmap_item.boundingRect()
                width = rect.width()
                height = rect.height()
                
                # 创建网格线
                pen = QPen(QColor(128, 128, 128, 100), 0.5)
                
                # 水平线
                for i in range(11):
                    y = rect.top() + (height / 10) * i
                    line = self._image_scene.addLine(rect.left(), y, rect.right(), y, pen)
                    self.grid_lines.append(line)
                
                # 垂直线
                for i in range(11):
                    x = rect.left() + (width / 10) * i
                    line = self._image_scene.addLine(x, rect.top(), x, rect.bottom(), pen)
                    self.grid_lines.append(line)
        
        def resetView(self):
            """
            重置视图
            """
            if self.pixmap_item:
                self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        
        def mousePressEvent(self, event):
            """
            处理鼠标按下事件
            """
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QMouseEvent
            
            self.last_mouse_pos = event.pos()
            super().mousePressEvent(event)
        
        def mouseMoveEvent(self, event):
            """
            处理鼠标移动事件
            """
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QMouseEvent
            
            if hasattr(self, 'last_mouse_pos'):
                delta_x = event.pos().x() - self.last_mouse_pos.x()
                delta_y = event.pos().y() - self.last_mouse_pos.y()
                
                # 发出拖动变化信号
                self.pan_changed.emit(delta_x, delta_y)
                
                self.last_mouse_pos = event.pos()
            
            super().mouseMoveEvent(event)
        
        def mouseReleaseEvent(self, event):
            """
            处理鼠标释放事件
            """
            from PySide6.QtCore import Qt
            
            if hasattr(self, 'last_mouse_pos'):
                delattr(self, 'last_mouse_pos')
            
            super().mouseReleaseEvent(event)
    
    def __init__(self, diff_result, parent=None):
        """
        初始化对比结果对话框
        
        Args:
            diff_result: 对比结果
            parent: 父组件
        """
        super().__init__(parent)
        self.diff_result = diff_result
        self.left_text: QTextEdit | None = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.right_text: QTextEdit | None = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self._left_to_right_scroll = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self._right_to_left_scroll = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self._sync_scroll_enabled = False  # pyright: ignore[reportUnannotatedClassAttribute]
        self.init_ui()
    
    def init_ui(self):
        """
        初始化对话框UI组件
        """
        from PySide6.QtWidgets import QPushButton, QSplitter, QTextEdit, QListWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
        from PySide6.QtCore import Qt
        
        # 设置对话框标题和大小
        self.setWindowTitle("文件对比结果")
        self.setMinimumSize(900, 700)
        # 显示最大化和最小化按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # 1. 最上方功能按钮（一行）
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # 文件操作按钮
        open_left_btn = QPushButton("打开左文件")
        open_left_btn.setFixedWidth(80)
        open_left_btn.clicked.connect(self._open_left_file)
        open_right_btn = QPushButton("打开右文件")
        open_right_btn.setFixedWidth(80)
        open_right_btn.clicked.connect(self._open_right_file)
        
        # 对比操作按钮
        compare_btn = QPushButton("开始对比")
        compare_btn.setFixedWidth(80)
        compare_btn.clicked.connect(self._start_compare)
        sync_btn = QPushButton("同步滚动")
        sync_btn.setFixedWidth(80)
        sync_btn.clicked.connect(self._toggle_sync_scroll)
        top_btn = QPushButton("滚动到顶")
        top_btn.setFixedWidth(80)
        top_btn.clicked.connect(self._scroll_to_top)
        
        # 导出操作按钮
        export_txt_btn = QPushButton("导出TXT")
        export_txt_btn.setFixedWidth(80)
        export_txt_btn.clicked.connect(lambda: self._export_report('txt'))
        export_html_btn = QPushButton("导出HTML")
        export_html_btn.setFixedWidth(80)
        export_html_btn.clicked.connect(lambda: self._export_report('html'))
        
        # 其他操作按钮
        init_btn = QPushButton("初始化")
        init_btn.setFixedWidth(80)
        init_btn.clicked.connect(self._initialize_app)
        exit_btn = QPushButton("退出")
        exit_btn.setFixedWidth(80)
        exit_btn.clicked.connect(self.close)
        
        # 添加按钮到工具栏
        # 只保留需要的按钮：同步滚动、滚动到顶、导出TXT、导出HTML、退出
        toolbar_layout.addWidget(sync_btn)
        toolbar_layout.addWidget(top_btn)
        toolbar_layout.addWidget(export_txt_btn)
        toolbar_layout.addWidget(export_html_btn)
        toolbar_layout.addWidget(exit_btn)
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # 2. 文件名（一行）
        file_names_frame = QFrame()
        file_names_frame.setFrameShape(QFrame.Shape.StyledPanel)
        file_names_frame.setFrameShadow(QFrame.Shadow.Raised)
        file_names_layout = QVBoxLayout(file_names_frame)
        file_names_layout.setContentsMargins(5, 5, 5, 5)
        file_names_layout.setSpacing(3)
        
        # 获取文件名
        if 'file1_path' in self.diff_result:
            file1_name = self.diff_result.get('file1_path', '左侧文件')
            file2_name = self.diff_result.get('file2_path', '右侧文件')
            
            file1_label = QLabel(f"左侧文件: {file1_name}")
            file1_label.setStyleSheet("font-weight: bold;")
            file2_label = QLabel(f"右侧文件: {file2_name}")
            file2_label.setStyleSheet("font-weight: bold;")
            
            file_names_layout.addWidget(file1_label)
            file_names_layout.addWidget(file2_label)
        elif 'folder1_path' in self.diff_result:
            folder1_name = self.diff_result.get('folder1_path', '左侧文件夹')
            folder2_name = self.diff_result.get('folder2_path', '右侧文件夹')
            
            folder1_label = QLabel(f"左侧文件夹: {folder1_name}")
            folder1_label.setStyleSheet("font-weight: bold;")
            folder2_label = QLabel(f"右侧文件夹: {folder2_name}")
            folder2_label.setStyleSheet("font-weight: bold;")
            
            file_names_layout.addWidget(folder1_label)
            file_names_layout.addWidget(folder2_label)
        
        main_layout.addWidget(file_names_frame)
        
        # 3. 2个对比文件显示框（自适应剩余空间行高）
        file_display_frame = QFrame()
        file_display_layout = QVBoxLayout(file_display_frame)
        file_display_layout.setContentsMargins(0, 0, 0, 0)
        file_display_layout.setSpacing(0)
        
        if 'folder1_path' in self.diff_result:
            # 文件夹对比结果
            self._setup_folder_diff_ui(file_display_layout)
        else:
            # 文件对比结果
            # 修改_setup_text_diff_ui调用，使其不包含文件名显示
            from PySide6.QtWidgets import QSplitter, QTextEdit, QVBoxLayout, QLabel, QFrame, QWidget
            from PySide6.QtCore import Qt
            
            # 获取文件类型
            file_type = self.diff_result.get('file_type', 'text')
            
            # 根据文件类型选择不同的显示方式
            if file_type == 'text' or file_type == 'document':
                # 文本文件或文档文件显示
                self._setup_text_display(file_display_layout)
            elif file_type == 'image':
                # 图片文件显示
                self._setup_image_display(file_display_layout)
            elif file_type == 'archive':
                # 压缩包文件显示
                self._setup_archive_display(file_display_layout)
            elif file_type == 'media':
                # 音视频文件显示
                self._setup_media_display(file_display_layout)
            else:
                # 其他类型文件显示
                self._setup_binary_display(file_display_layout)
        
        # 移除内部伸缩项，让file_display_frame本身能够填充剩余空间
        # file_display_layout.addStretch()
        
        # 添加file_display_frame到main_layout，并设置伸展因子为1，使其填充剩余空间
        main_layout.addWidget(file_display_frame, 1)
        
        # 移除多余的伸缩项，因为file_display_frame已经设置了伸展因子
        # main_layout.addStretch()
        
        # 4. 分析结果和图例组合框（置底显示）
        combined_frame = QFrame()
        combined_frame.setFrameShape(QFrame.Shape.StyledPanel)
        combined_frame.setFrameShadow(QFrame.Shadow.Raised)
        combined_layout = QVBoxLayout(combined_frame)
        combined_layout.setContentsMargins(5, 5, 5, 5)
        combined_layout.setSpacing(10)
        
        # 分析结果部分
        analysis_title = QLabel("对比分析结果")
        analysis_title.setStyleSheet("font-weight: bold;")
        combined_layout.addWidget(analysis_title)
        
        # 分析结果内容
        analysis_content = QGridLayout()
        analysis_content.setSpacing(5)
        
        # 计算分析结果
        analysis_results = self._analyze_diff_result()
        
        # 限制显示5行关键信息
        key_items = list(analysis_results.items())[:5]
        
        # 添加分析结果项
        row = 0
        for key, value in key_items:
            label = QLabel(f"{key}:")
            value_label = QLabel(str(value))
            analysis_content.addWidget(label, row, 0, 1, 1)
            analysis_content.addWidget(value_label, row, 1, 1, 3)
            row += 1
        
        combined_layout.addLayout(analysis_content)
        
        # 图例部分
        legend_title = QLabel("对比图例:")
        combined_layout.addWidget(legend_title)
        
        # 图例内容
        legend_content = QHBoxLayout()
        legend_content.setSpacing(10)
        
        # 添加图例项
        legend_items = [
            ("红色", "删除的内容", "#FF0000"),
            ("绿色", "添加的内容", "#008000"),
            ("蓝色", "修改的内容", "#0000FF"),
            ("灰色", "相同的内容", "#808080")
        ]
        
        for color_name, description, color_code in legend_items:
            legend_item = QHBoxLayout()
            color_box = QLabel()
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(f"background-color: {color_code};")
            color_label = QLabel(f"{color_name}")
            desc_label = QLabel(f"{description}")
            legend_item.addWidget(color_box)
            legend_item.addWidget(color_label)
            legend_item.addWidget(desc_label)
            legend_content.addLayout(legend_item)
        
        legend_content.addStretch()
        combined_layout.addLayout(legend_content)
        
        # 将组合框添加到主布局
        main_layout.addWidget(combined_frame)
    
    def _setup_text_diff_ui(self, layout):
        """
        设置文本对比结果UI
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QTextEdit, QVBoxLayout, QLabel, QFrame, QWidget
        from PySide6.QtCore import Qt
        
        # 获取文件类型
        file_type = self.diff_result.get('file_type', 'text')
        
        # 创建对比容器
        compare_container = QFrame()
        compare_layout = QVBoxLayout(compare_container)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(0)
        
        # 添加文件名显示（左上方）
        file_names_layout = QFrame()
        file_names_layout.setFrameShape(QFrame.Shape.StyledPanel)
        file_names_layout.setFrameShadow(QFrame.Shadow.Raised)
        file_names_inner_layout = QVBoxLayout(file_names_layout)
        file_names_inner_layout.setContentsMargins(5, 5, 5, 5)
        file_names_inner_layout.setSpacing(2)
        
        # 获取文件名
        file1_name = self.diff_result.get('file1_path', '左侧文件')
        file2_name = self.diff_result.get('file2_path', '右侧文件')
        
        file1_label = QLabel(f"左侧文件: {file1_name}")
        file1_label.setStyleSheet("font-size: 12px; color: #666;")
        file2_label = QLabel(f"右侧文件: {file2_name}")
        file2_label.setStyleSheet("font-size: 12px; color: #666;")
        
        file_names_inner_layout.addWidget(file1_label)
        file_names_inner_layout.addWidget(file2_label)
        compare_layout.addWidget(file_names_layout)
        
        # 根据文件类型选择不同的显示方式
        if file_type == 'text':
            # 文本文件显示
            self._setup_text_display(compare_layout)
        elif file_type == 'image':
            # 图片文件显示
            self._setup_image_display(compare_layout)
        elif file_type == 'archive':
            # 压缩包文件显示
            self._setup_archive_display(compare_layout)
        elif file_type == 'media':
            # 音视频文件显示
            self._setup_media_display(compare_layout)
        else:
            # 其他类型文件显示
            self._setup_binary_display(compare_layout)
        
        layout.addWidget(compare_container)
    
    def _setup_text_display(self, layout):
        """
        设置文本文件显示
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QTextEdit
        from PySide6.QtCore import Qt
        
        # 添加对比结果显示区域
        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧文件内容
        self.left_text = QTextEdit()
        self.left_text.setReadOnly(True)
        self.left_text.setPlaceholderText("左侧文件内容")
        
        # 右侧文件内容
        self.right_text = QTextEdit()
        self.right_text.setReadOnly(True)
        self.right_text.setPlaceholderText("右侧文件内容")
        
        result_splitter.addWidget(self.left_text)
        result_splitter.addWidget(self.right_text)
        result_splitter.setSizes([400, 400])
        
        layout.addWidget(result_splitter)
        
        # 显示对比结果
        self._display_text_diff(self.left_text, self.right_text)
                
    def _setup_image_display(self, layout):
        """
        设置图片文件显示
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QHBoxLayout, QPushButton, QWidget, QCheckBox, QVBoxLayout
        from PySide6.QtCore import Qt
        
        # 创建一个垂直布局容器，用于容纳控制按钮和图片显示区域
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setSpacing(0)
        
        # 添加图片显示区域
        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建左侧图片查看器
        left_viewer = self.ImageViewer()
        
        # 创建右侧图片查看器
        right_viewer = self.ImageViewer()
        
        # 创建控制按钮（置顶显示）
        control_widget = QWidget()
        control_widget.setStyleSheet("background-color: #f0f0f0; border-bottom: 1px solid #ddd;")
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(10)
        
        # 重置按钮
        reset_btn = QPushButton("重置视图")
        reset_btn.clicked.connect(lambda: (left_viewer.resetView(), right_viewer.resetView()))
        
        # 显示/隐藏网格按钮
        grid_btn = QPushButton("显示网格")
        grid_btn.clicked.connect(lambda: (left_viewer.toggleGrid(), right_viewer.toggleGrid()))
        
        # 同步缩放复选框
        sync_zoom_checkbox = QCheckBox("同步缩放")
        sync_zoom_checkbox.setChecked(True)
        
        # 同步拖动复选框
        sync_pan_checkbox = QCheckBox("同步拖动")
        sync_pan_checkbox.setChecked(True)
        
        control_layout.addWidget(reset_btn)
        control_layout.addWidget(grid_btn)
        control_layout.addWidget(sync_zoom_checkbox)
        control_layout.addWidget(sync_pan_checkbox)
        control_layout.addStretch()
        
        # 添加控制按钮到容器布局
        image_container_layout.addWidget(control_widget)
        
        result_splitter.addWidget(left_viewer)
        result_splitter.addWidget(right_viewer)
        result_splitter.setSizes([400, 400])
        
        # 同步缩放功能
        def sync_zoom(source_viewer, target_viewer, scale):
            if sync_zoom_checkbox.isChecked():
                # 保存当前滚动条位置比例
                if source_viewer.horizontalScrollBar().maximum() > 0:
                    h_ratio = source_viewer.horizontalScrollBar().value() / source_viewer.horizontalScrollBar().maximum()
                else:
                    h_ratio = 0
                
                if source_viewer.verticalScrollBar().maximum() > 0:
                    v_ratio = source_viewer.verticalScrollBar().value() / source_viewer.verticalScrollBar().maximum()
                else:
                    v_ratio = 0
                
                # 应用缩放
                target_viewer.setTransform(source_viewer.transform())
                
                # 恢复滚动条位置比例
                if target_viewer.horizontalScrollBar().maximum() > 0:
                    target_viewer.horizontalScrollBar().setValue(int(h_ratio * target_viewer.horizontalScrollBar().maximum()))
                if target_viewer.verticalScrollBar().maximum() > 0:
                    target_viewer.verticalScrollBar().setValue(int(v_ratio * target_viewer.verticalScrollBar().maximum()))
        
        # 同步拖动功能
        def sync_pan(source_viewer, target_viewer, delta_x, delta_y):
            if sync_pan_checkbox.isChecked():
                # 应用相同的拖动操作
                target_viewer.horizontalScrollBar().setValue(target_viewer.horizontalScrollBar().value() - delta_x)
                target_viewer.verticalScrollBar().setValue(target_viewer.verticalScrollBar().value() - delta_y)
        
        # 连接缩放信号
        left_viewer.zoom_changed.connect(lambda scale: sync_zoom(left_viewer, right_viewer, scale))
        right_viewer.zoom_changed.connect(lambda scale: sync_zoom(right_viewer, left_viewer, scale))
        
        # 连接拖动信号
        left_viewer.pan_changed.connect(lambda delta_x, delta_y: sync_pan(left_viewer, right_viewer, delta_x, delta_y))
        right_viewer.pan_changed.connect(lambda delta_x, delta_y: sync_pan(right_viewer, left_viewer, delta_x, delta_y))
        
        # 添加图片显示区域到容器布局
        image_container_layout.addWidget(result_splitter, 1)  # 设置伸展因子为1，使其填充剩余空间
        
        # 添加容器到主布局
        layout.addWidget(image_container)
        
        # 显示图片
        self._display_image_diff(left_viewer, right_viewer)
    
    def _setup_archive_display(self, layout):
        """
        设置压缩包文件显示
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QTextEdit
        from PySide6.QtCore import Qt
        
        # 添加压缩包内容显示区域
        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧压缩包内容
        left_archive = QTextEdit()
        left_archive.setReadOnly(True)
        left_archive.setPlaceholderText("左侧压缩包内容")
        
        # 右侧压缩包内容
        right_archive = QTextEdit()
        right_archive.setReadOnly(True)
        right_archive.setPlaceholderText("右侧压缩包内容")
        
        result_splitter.addWidget(left_archive)
        result_splitter.addWidget(right_archive)
        result_splitter.setSizes([400, 400])
        
        layout.addWidget(result_splitter)
        
        # 显示压缩包内容
        self._display_archive_diff(left_archive, right_archive)
    
    def _setup_media_display(self, layout):
        """
        设置音视频文件显示
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QTextEdit
        from PySide6.QtCore import Qt
        
        # 添加音视频信息显示区域
        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧音视频信息
        left_media = QTextEdit()
        left_media.setReadOnly(True)
        left_media.setPlaceholderText("左侧音视频信息")
        
        # 右侧音视频信息
        right_media = QTextEdit()
        right_media.setReadOnly(True)
        right_media.setPlaceholderText("右侧音视频信息")
        
        result_splitter.addWidget(left_media)
        result_splitter.addWidget(right_media)
        result_splitter.setSizes([400, 400])
        
        layout.addWidget(result_splitter)
        
        # 显示音视频信息
        self._display_media_diff(left_media, right_media)
    
    def _setup_binary_display(self, layout):
        """
        设置二进制文件显示
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QSplitter, QTextEdit
        from PySide6.QtCore import Qt
        
        # 添加二进制内容显示区域
        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧二进制内容
        left_binary = QTextEdit()
        left_binary.setReadOnly(True)
        left_binary.setPlaceholderText("左侧文件内容")
        
        # 右侧二进制内容
        right_binary = QTextEdit()
        right_binary.setReadOnly(True)
        right_binary.setPlaceholderText("右侧文件内容")
        
        result_splitter.addWidget(left_binary)
        result_splitter.addWidget(right_binary)
        result_splitter.setSizes([400, 400])
        
        layout.addWidget(result_splitter)
        
        # 显示二进制内容
        self._display_binary_diff(left_binary, right_binary)
    
    def _setup_folder_diff_ui(self, layout):
        """
        设置文件夹对比结果UI
        
        Args:
            layout: 布局对象
        """
        from PySide6.QtWidgets import QListWidget
        
        # 添加文件夹对比结果显示
        folder_result_list = QListWidget()
        layout.addWidget(folder_result_list)
        
        # 显示对比结果
        self._display_folder_diff(folder_result_list)
    
    def _display_text_diff(self, left_text, right_text):
        """
        显示文本文件对比结果
        
        Args:
            left_text: 左侧文本框
            right_text: 右侧文本框
        """
        # 清空现有内容
        left_text.clear()
        right_text.clear()
        
        # 设置编码为UTF-8，确保正确显示各种字符
        left_text.setAcceptRichText(True)
        right_text.setAcceptRichText(True)
        
        # 构建左右文本内容，带行号
        left_content = []
        right_content = []
        line_number = 1
        
        for line in self.diff_result['diff_lines']:
            # 添加行号
            line_num_str = f"<font color='#808080'>{line_number:4d}</font> "
            
            # 确保内容是字符串类型，避免编码错误
            content = str(line['content']) if line['content'] is not None else ''
            
            if line['type'] == 'equal':
                left_content.append(f"{line_num_str}{content}")
                right_content.append(f"{line_num_str}{content}")
                line_number += 1
            elif line['type'] == 'delete':
                left_content.append(f"{line_num_str}<font color='red'>{content}</font>")
                right_content.append(f"{line_num_str}")
                line_number += 1
            elif line['type'] == 'add':
                left_content.append(f"{line_num_str}")
                right_content.append(f"{line_num_str}<font color='green'>{content}</font>")
                line_number += 1
        
        # 设置内容，使用UTF-8编码
        left_text.setHtml('<br>'.join(left_content))
        right_text.setHtml('<br>'.join(right_content))
    
    def _display_image_diff(self, left_viewer, right_viewer):
        """
        显示图片文件对比结果
        
        Args:
            left_viewer: 左侧图片查看器
            right_viewer: 右侧图片查看器
        """
        from PySide6.QtGui import QPixmap
        
        # 加载图片
        left_pixmap = QPixmap(self.diff_result['file1_path'])
        right_pixmap = QPixmap(self.diff_result['file2_path'])
        
        # 设置图片到查看器
        left_viewer.setPixmap(left_pixmap)
        right_viewer.setPixmap(right_pixmap)
        
        # 设置图片信息
        file1_info = self.diff_result.get('file1_info', {})
        file2_info = self.diff_result.get('file2_info', {})
        
        left_viewer.setToolTip(f"格式: {file1_info.get('format', '未知')}\n大小: {file1_info.get('size', '未知')}\n模式: {file1_info.get('mode', '未知')}")
        right_viewer.setToolTip(f"格式: {file2_info.get('format', '未知')}\n大小: {file2_info.get('size', '未知')}\n模式: {file2_info.get('mode', '未知')}")
    
    def _display_archive_diff(self, left_archive, right_archive):
        """
        显示压缩包文件对比结果
        
        Args:
            left_archive: 左侧压缩包内容文本框
            right_archive: 右侧压缩包内容文本框
        """
        # 获取压缩包内容
        file1_contents = self.diff_result.get('file1_contents', [])
        file2_contents = self.diff_result.get('file2_contents', [])
        
        # 构建左侧内容
        left_content = ["压缩包内容:"]
        for file in file1_contents:
            left_content.append(f"- {file}")
        
        # 构建右侧内容
        right_content = ["压缩包内容:"]
        for file in file2_contents:
            right_content.append(f"- {file}")
        
        # 设置内容
        left_archive.setPlainText('\n'.join(left_content))
        right_archive.setPlainText('\n'.join(right_content))
    
    def _display_media_diff(self, left_media, right_media):
        """
        显示音视频文件对比结果
        
        Args:
            left_media: 左侧音视频信息文本框
            right_media: 右侧音视频信息文本框
        """
        # 获取音视频信息
        file1_info = self.diff_result.get('file1_info', {})
        file2_info = self.diff_result.get('file2_info', {})
        
        # 构建左侧内容
        left_content = ["音视频信息:"]
        for key, value in file1_info.items():
            left_content.append(f"{key}: {value}")
        
        # 构建右侧内容
        right_content = ["音视频信息:"]
        for key, value in file2_info.items():
            right_content.append(f"{key}: {value}")
        
        # 设置内容
        left_media.setPlainText('\n'.join(left_content))
        right_media.setPlainText('\n'.join(right_content))
    
    def _display_binary_diff(self, left_binary, right_binary):
        """
        显示二进制文件对比结果
        
        Args:
            left_binary: 左侧二进制内容文本框
            right_binary: 右侧二进制内容文本框
        """
        # 读取二进制文件并转换为十六进制+文本格式
        def read_binary_file(file_path):
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # 转换为十六进制+文本格式
                hex_text = []
                for i in range(0, len(data), 16):
                    chunk = data[i:i+16]
                    # 十六进制部分
                    hex_part = ' '.join([f'{b:02x}' for b in chunk])
                    # 文本部分（可打印字符）
                    text_part = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in chunk])
                    # 行号
                    line_num = f'{i:08x}'
                    # 格式：行号 | 十六进制（16字节） | 文本
                    hex_text.append(f'{line_num} | {hex_part:<47} | {text_part}')
                
                return '\n'.join(hex_text)
            except Exception as e:
                logger.debug(f"读取文件失败: {e}")
                return f"读取文件失败: {str(e)}"
        
        # 获取文件路径
        file1_path = self.diff_result.get('file1_path', '')
        file2_path = self.diff_result.get('file2_path', '')
        
        # 构建左侧内容
        left_content = ["二进制文件 (十六进制+文本):"]
        left_content.append("=" * 80)
        if file1_path:
            left_content.append(read_binary_file(file1_path))
        else:
            left_content.append("文件路径不存在")
        
        # 构建右侧内容
        right_content = ["二进制文件 (十六进制+文本):"]
        right_content.append("=" * 80)
        if file2_path:
            right_content.append(read_binary_file(file2_path))
        else:
            right_content.append("文件路径不存在")
        
        # 设置内容
        left_binary.setPlainText('\n'.join(left_content))
        right_binary.setPlainText('\n'.join(right_content))
    
    def _display_folder_diff(self, folder_result_list):
        """
        显示文件夹对比结果
        
        Args:
            folder_result_list: 文件夹结果列表
        """
        # 清空现有内容
        folder_result_list.clear()
        
        # 添加共同文件
        if self.diff_result['common_files']:
            folder_result_list.addItem("<font color='blue'><b>共同文件:</b></font>")
            for file in self.diff_result['common_files']:
                folder_result_list.addItem(f"  {file}")
        
        # 添加仅在左侧存在的文件
        if self.diff_result['only_in_folder1']:
            folder_result_list.addItem("<font color='orange'><b>仅在左侧文件夹存在:</b></font>")
            for file in self.diff_result['only_in_folder1']:
                folder_result_list.addItem(f"  {file}")
        
        # 添加仅在右侧存在的文件
        if self.diff_result['only_in_folder2']:
            folder_result_list.addItem("<font color='purple'><b>仅在右侧文件夹存在:</b></font>")
            for file in self.diff_result['only_in_folder2']:
                folder_result_list.addItem(f"  {file}")
    
    def _open_left_file(self):
        """
        打开左侧文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择左侧文件", ".", "所有文件 (*.*)"
        )
        
        if file_path:
            # 这里可以添加文件打开逻辑
            logger.debug(f"打开左侧文件: {file_path}")
    
    def _open_right_file(self):
        """
        打开右侧文件
        """
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择右侧文件", ".", "所有文件 (*.*)"
        )
        
        if file_path:
            # 这里可以添加文件打开逻辑
            logger.debug(f"打开右侧文件: {file_path}")
    
    def _start_compare(self):
        """
        开始对比
        """
        logger.debug("开始对比")
        # 这里可以添加对比逻辑
    
    def _toggle_sync_scroll(self):
        """
        切换同步滚动
        """
        logger.debug("切换同步滚动")
        # 检查是否存在文本编辑器组件
        if hasattr(self, 'left_text') and hasattr(self, 'right_text'):
            # 检查是否已经连接了滚动信号
            if not hasattr(self, '_sync_scroll_enabled') or not self._sync_scroll_enabled:
                # 启用同步滚动
                # 保存连接的槽函数引用，以便后续可以精确断开
                self._left_to_right_scroll = lambda value: self.right_text.verticalScrollBar().setValue(value)
                self._right_to_left_scroll = lambda value: self.left_text.verticalScrollBar().setValue(value)
                
                # 连接信号
                self.left_text.verticalScrollBar().valueChanged.connect(self._left_to_right_scroll)
                self.right_text.verticalScrollBar().valueChanged.connect(self._right_to_left_scroll)
                
                self._sync_scroll_enabled = True
                logger.debug("同步滚动已启用")
            else:
                # 禁用同步滚动
                try:
                    # 精确断开我们添加的槽函数，而不是断开所有槽函数
                    if hasattr(self, '_left_to_right_scroll'):
                        self.left_text.verticalScrollBar().valueChanged.disconnect(self._left_to_right_scroll)
                    if hasattr(self, '_right_to_left_scroll'):
                        self.right_text.verticalScrollBar().valueChanged.disconnect(self._right_to_left_scroll)
                    
                    # 清理引用
                    delattr(self, '_left_to_right_scroll')
                    delattr(self, '_right_to_left_scroll')
                except Exception as e:
                    logger.error(f"断开滚动信号时发生错误: {e}")
                
                self._sync_scroll_enabled = False
                logger.debug("同步滚动已禁用")

    def _scroll_to_top(self):
        """
        滚动到顶部
        """
        logger.debug("滚动到顶部")
        # 检查是否存在文本编辑器组件
        if hasattr(self, 'left_text') and hasattr(self, 'right_text'):
            # 滚动到顶部
            self.left_text.verticalScrollBar().setValue(0)
            self.right_text.verticalScrollBar().setValue(0)
            logger.debug("已滚动到顶部")
    
    def _initialize_app(self):
        """
        初始化应用
        """
        logger.debug("初始化应用")
        # 这里可以添加初始化逻辑
    
    def _analyze_diff_result(self):
        """
        分析对比结果，生成统计信息
        
        Returns:
            dict: 分析结果字典
        """
        import os
        from datetime import datetime
        
        analysis_results = {}
        
        # 添加对比时间戳
        analysis_results['对比时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'diff_lines' in self.diff_result:
            # 文本文件对比分析
            diff_lines = self.diff_result['diff_lines']
            total_lines = len(diff_lines)
            
            # 统计不同类型的修改
            added_lines = 0
            deleted_lines = 0
            modified_lines = 0
            same_lines = 0
            total_chars = 0
            
            for line in diff_lines:
                if line['type'] == 'add':
                    added_lines += 1
                    total_chars += len(line.get('content', ''))
                elif line['type'] == 'delete':
                    deleted_lines += 1
                    total_chars += len(line.get('content', ''))
                elif line['type'] == 'equal':
                    same_lines += 1
                    total_chars += len(line.get('content', ''))
                elif line['type'] == 'modify':
                    modified_lines += 1
                    total_chars += len(line.get('content', ''))
            
            # 计算相似度
            similarity = (same_lines / total_lines * 100) if total_lines > 0 else 0
            
            # 构建分析结果
            analysis_results.update({
                '文件类型': '文本文件',
                '总行数': total_lines,
                '总字符数': total_chars,
                '相同行数': same_lines,
                '添加行数': added_lines,
                '删除行数': deleted_lines,
                '修改行数': modified_lines,
                '相似度': f"{similarity:.2f}%",
                '修改率': f"{((added_lines + deleted_lines + modified_lines) / total_lines * 100):.2f}%" if total_lines > 0 else "0.00%"
            })
        elif 'common_files' in self.diff_result:
            # 文件夹对比分析
            common_files = self.diff_result['common_files']
            only_in_folder1 = self.diff_result['only_in_folder1']
            only_in_folder2 = self.diff_result['only_in_folder2']
            
            total_files = len(common_files) + len(only_in_folder1) + len(only_in_folder2)
            similarity = (len(common_files) / total_files * 100) if total_files > 0 else 0
            
            # 构建分析结果
            analysis_results.update({
                '文件类型': '文件夹',
                '总文件数': total_files,
                '共同文件数': len(common_files),
                '仅在左侧文件夹': len(only_in_folder1),
                '仅在右侧文件夹': len(only_in_folder2),
                '相似度': f"{similarity:.2f}%",
                '差异率': f"{((len(only_in_folder1) + len(only_in_folder2)) / total_files * 100):.2f}%" if total_files > 0 else "0.00%"
            })
        
        # 添加文件路径信息
        if 'file1_path' in self.diff_result:
            analysis_results['左侧文件'] = os.path.basename(self.diff_result['file1_path'])
        if 'file2_path' in self.diff_result:
            analysis_results['右侧文件'] = os.path.basename(self.diff_result['file2_path'])
        
        return analysis_results
    
    def _export_report(self, report_type):
        """
        导出对比报告
        
        Args:
            report_type: 报告类型，可选值：'txt', 'html'
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from services.file_diff_service import file_diff_service
        
        if not self.diff_result:
            QMessageBox.warning(self, "警告", "没有对比结果可导出")
            return
        
        # 打开文件保存对话框
        if report_type == 'txt':
            default_ext = '.txt'
            filter = '文本文件 (*.txt)'
        else:
            default_ext = '.html'
            filter = 'HTML文件 (*.html)'
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, f"导出{report_type.upper()}报告", ".", filter
        )
        
        if output_path:
            if not output_path.endswith(default_ext):
                output_path += default_ext
            
            # 导出报告
            success = file_diff_service.export_diff_report(
                self.diff_result, output_path, report_type
            )
            
            if success:
                QMessageBox.information(self, "成功", f"报告已导出到: {output_path}")
            else:
                QMessageBox.critical(self, "错误", "导出失败")
