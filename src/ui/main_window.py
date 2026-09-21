#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块
负责构建应用程序的主界面框架
"""

import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar,
    QVBoxLayout, QHBoxLayout, QWidget, QToolButton, QComboBox,
    QLabel, QApplication
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QSize, QTimer
from core.config import config_manager
from core.logger import logger
from ui.dual_pane import DualPane
from services.system_monitor import SystemMonitor
from services.transfer_monitor import TransferMonitor

class MainWindow(QMainWindow):
    """
    主窗口类
    构建应用程序的主界面框架
    """
    
    def __init__(self):
        """
        初始化主窗口
        """
        super().__init__()
        
        # 初始化系统资源数据
        self._current_cpu_percent = 0.0
        self._current_memory_percent = 0.0
        
        self.init_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        self.setup_theme()
        self.setup_timers()
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self._check_and_resume_whoosh_index)
        
        logger.info("主窗口已初始化")
    
    def init_ui(self):
        """
        初始化UI组件
        """
        # 设置窗口标题和大小
        app_title = config_manager.get("ui.app_title", "AFM-EST - 全能资源搜索管理器")
        self.setWindowTitle(app_title)
        window_size = config_manager.get("ui.window_size")
        self.resize(window_size[0], window_size[1])
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建双窗格组件
        self.dual_pane = DualPane()
        main_layout.addWidget(self.dual_pane)
        
        # 设置分隔器比例
        splitter_ratio = config_manager.get("ui.splitter_ratio")
        self.dual_pane.set_splitter_ratio(splitter_ratio)
        
        # 加载功能面板可见状态
        function_panel_visible = config_manager.get("ui.function_panel_visible", True)
        self.dual_pane.function_panel.setVisible(function_panel_visible)
        
        # 初始化显示隐藏文件状态
        show_hidden = config_manager.get("ui.show_hidden_files")
        self.dual_pane.set_show_hidden_files(show_hidden)

        # 初始化左右窗格路径（跨平台兼容）
        import os

        # 获取系统默认路径
        if os.name == 'nt':  # Windows
            default_path = "C:/"
        else:  # Linux/macOS
            default_path = os.path.expanduser("~")  # 用户主目录

        remember_last_path = config_manager.get("ui.remember_last_path", True)
        if remember_last_path:
            # 加载保存的路径
            left_path = config_manager.get("ui.left_pane_path", default_path)
            right_path = config_manager.get("ui.right_pane_path", default_path)

            # 检查路径是否存在（跨平台兼容）
            if not os.path.exists(left_path) or (os.name != 'nt' and (left_path.startswith("C:") or left_path.startswith("c:"))):
                left_path = default_path
            if not os.path.exists(right_path) or (os.name != 'nt' and (right_path.startswith("C:") or right_path.startswith("c:"))):
                right_path = default_path

            logger.info(f"加载左右窗格路径: {left_path}, {right_path}")
        else:
            # 使用默认路径
            left_path = default_path
            right_path = default_path
        
        # 设置左右窗格路径
        self.dual_pane.get_left_pane().set_current_path(left_path)
        self.dual_pane.get_right_pane().set_current_path(right_path)
        
        # 初始化焦点样式（左窗格有焦点，右窗格无焦点）
        self.dual_pane.get_left_pane()._update_address_bar_style(True)
        self.dual_pane.get_right_pane()._update_address_bar_style(False)
    
    def setup_menus(self):
        """
        设置菜单栏
        """
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        # 新建菜单
        new_menu = file_menu.addMenu("新建")
        new_folder_action = QAction("文件夹", self)
        new_folder_action.setShortcut("Ctrl+Shift+N")
        new_folder_action.triggered.connect(lambda: self.dual_pane.get_active_pane().create_new_folder())
        new_file_action = QAction("文件", self)
        new_file_action.setShortcut("Ctrl+N")
        new_file_action.triggered.connect(lambda: self.dual_pane.get_active_pane().create_new_file())
        new_menu.addAction(new_folder_action)
        new_menu.addAction(new_file_action)
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        cut_action = QAction("剪切", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.dual_pane.get_active_pane().cut_selected_items())
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.dual_pane.get_active_pane().copy_selected_items())
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.dual_pane.get_active_pane().paste_items())
        delete_action = QAction("删除", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(lambda: self.dual_pane.get_active_pane().delete_selected_items())
        rename_action = QAction("重命名", self)
        rename_action.setShortcut("F2")
        rename_action.triggered.connect(lambda: self.dual_pane.get_active_pane()._on_rename_clicked())
        
        edit_menu.addAction(cut_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(delete_action)
        edit_menu.addAction(rename_action)
        
        # 查看菜单
        view_menu = menu_bar.addMenu("查看")
        
        # 视图模式子菜单
        view_mode_menu = view_menu.addMenu("视图模式")
        self.icon_view_action = QAction("图标视图", self, checkable=True)
        self.icon_view_action.setShortcut("Ctrl+1")
        self.list_view_action = QAction("列表视图", self, checkable=True)
        self.list_view_action.setShortcut("Ctrl+2")
        self.detail_view_action = QAction("详细信息", self, checkable=True)
        self.detail_view_action.setShortcut("Ctrl+3")
        self.thumbnail_view_action = QAction("缩略图", self, checkable=True)
        self.thumbnail_view_action.setShortcut("Ctrl+4")
        self.tile_view_action = QAction("平铺", self, checkable=True)
        self.tile_view_action.setShortcut("Ctrl+5")
        
        # 为视图模式菜单项添加事件处理
        self.icon_view_action.triggered.connect(lambda checked: self.set_view_mode("icon"))
        self.list_view_action.triggered.connect(lambda checked: self.set_view_mode("list"))
        self.detail_view_action.triggered.connect(lambda checked: self.set_view_mode("detail"))
        self.thumbnail_view_action.triggered.connect(lambda checked: self.set_view_mode("thumbnail"))
        self.tile_view_action.triggered.connect(lambda checked: self.set_view_mode("tile"))
        
        view_mode_menu.addAction(self.icon_view_action)
        view_mode_menu.addAction(self.list_view_action)
        view_mode_menu.addAction(self.detail_view_action)
        view_mode_menu.addAction(self.thumbnail_view_action)
        view_mode_menu.addAction(self.tile_view_action)
        
        # 分组子菜单
        group_menu = view_menu.addMenu("分组")
        self.no_group_action = QAction("无分组", self, checkable=True)
        self.no_group_action.setShortcut("Ctrl+Alt+0")
        self.group_by_type_action = QAction("按类型", self, checkable=True)
        self.group_by_type_action.setShortcut("Ctrl+Alt+1")
        self.group_by_date_action = QAction("按日期", self, checkable=True)
        self.group_by_date_action.setShortcut("Ctrl+Alt+2")
        self.group_by_size_action = QAction("按大小", self, checkable=True)
        self.group_by_size_action.setShortcut("Ctrl+Alt+3")
        
        # 为分组菜单项添加事件处理
        self.no_group_action.triggered.connect(lambda checked: self.set_group_mode("none"))
        self.group_by_type_action.triggered.connect(lambda checked: self.set_group_mode("type"))
        self.group_by_date_action.triggered.connect(lambda checked: self.set_group_mode("date"))
        self.group_by_size_action.triggered.connect(lambda checked: self.set_group_mode("size"))
        
        group_menu.addAction(self.no_group_action)
        group_menu.addAction(self.group_by_type_action)
        group_menu.addAction(self.group_by_date_action)
        group_menu.addAction(self.group_by_size_action)
        
        # 初始化菜单勾选状态
        self.update_menu_check_states()
        
        # 显示隐藏文件
        self.show_hidden_action = QAction("显示隐藏文件", self, checkable=True)
        self.show_hidden_action.setShortcut("Ctrl+H")
        self.show_hidden_action.triggered.connect(self.toggle_hidden_files)
        # 根据配置文件初始化选中状态
        show_hidden = config_manager.get("ui.show_hidden_files")
        self.show_hidden_action.setChecked(show_hidden)
        view_menu.addAction(self.show_hidden_action)
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(lambda: self.dual_pane.get_active_pane().refresh())
        view_menu.addAction(refresh_action)
        
        # 主题子菜单
        theme_menu = view_menu.addMenu("主题")
        self.light_theme_action = QAction("浅色主题", self, checkable=True)
        self.dark_theme_action = QAction("深色主题", self, checkable=True)
        self.system_theme_action = QAction("系统主题", self, checkable=True)
        
        theme_group = [self.light_theme_action, self.dark_theme_action, self.system_theme_action]
        for action in theme_group:
            action.triggered.connect(lambda checked=False, a=action: self.change_theme(a.text()))
            theme_menu.addAction(action)
        
        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        batch_rename_action = QAction("批量重命名", self)
        batch_rename_action.setShortcut("Ctrl+R")
        encode_convert_action = QAction("文件编码转换", self)
        encode_convert_action.setShortcut("Ctrl+E")
        image_convert_action = QAction("图片格式转换", self)
        image_convert_action.setShortcut("Ctrl+I")
        file_checksum_action = QAction("文件校验", self)
        file_checksum_action.setShortcut("Ctrl+K")
        
        # 为工具菜单项添加事件处理，激活辅助标签内的相应子标签
        batch_rename_action.triggered.connect(lambda: self.dual_pane.switch_to_tools_tab("批量重命名"))
        encode_convert_action.triggered.connect(lambda: self.dual_pane.switch_to_tools_tab("编码转换"))
        image_convert_action.triggered.connect(lambda: self.dual_pane.switch_to_tools_tab("图片转换"))
        file_checksum_action.triggered.connect(lambda: self.dual_pane.switch_to_tools_tab("文件校验"))
        
        tools_menu.addAction(batch_rename_action)
        tools_menu.addAction(encode_convert_action)
        tools_menu.addAction(image_convert_action)
        tools_menu.addAction(file_checksum_action)
        
        # 搜索索引
        tools_menu.addSeparator()
        build_index_action = QAction("创建搜索索引", self)
        build_index_action.setShortcut("Ctrl+Shift+I")
        build_index_action.triggered.connect(self.build_search_index)
        tools_menu.addAction(build_index_action)
        
        clear_index_action = QAction("清除已创建索引", self)
        clear_index_action.setShortcut("Ctrl+Shift+Del")
        clear_index_action.triggered.connect(self.clear_search_index)
        tools_menu.addAction(clear_index_action)
        
        open_index_action = QAction("打开索引文件夹", self)
        open_index_action.setShortcut("Ctrl+Shift+O")
        open_index_action.triggered.connect(self.open_index_folder)
        tools_menu.addAction(open_index_action)
        
        # 设置子菜单
        settings_action = QAction("设置", self)
        settings_action.setShortcut("Ctrl+S")
        settings_action.triggered.connect(self.show_settings_dialog)
        tools_menu.addAction(settings_action)
        
        # 传输菜单
        transfer_menu = menu_bar.addMenu("传输")
        ftp_connect_action = QAction("FTP连接", self)
        ftp_connect_action.setShortcut("Ctrl+F")
        p2p_transfer_action = QAction("点对点传输", self)
        p2p_transfer_action.setShortcut("Ctrl+P")
        transfer_history_action = QAction("传输历史", self)
        transfer_history_action.setShortcut("Ctrl+Shift+H")
        
        # 为传输菜单项添加事件处理，激活传输面板
        ftp_connect_action.triggered.connect(lambda: self.dual_pane.switch_function_panel_tab("Ftp"))
        p2p_transfer_action.triggered.connect(lambda: self.dual_pane.switch_function_panel_tab("P2P"))
        transfer_history_action.triggered.connect(lambda: self.dual_pane.switch_function_panel_tab("Ftp"))
        
        transfer_menu.addAction(ftp_connect_action)
        transfer_menu.addAction(p2p_transfer_action)
        transfer_menu.addAction(transfer_history_action)
        
        # 对比菜单
        compare_menu = menu_bar.addMenu("对比")
        compare_files_action = QAction("对比文件", self)
        compare_files_action.setShortcut("Ctrl+B")
        compare_folders_action = QAction("对比文件夹", self)
        compare_folders_action.setShortcut("Ctrl+Alt+B")
        
        # 为对比菜单项添加事件处理，激活对比面板
        compare_files_action.triggered.connect(lambda: self.dual_pane.switch_function_panel_tab("对比"))
        compare_folders_action.triggered.connect(lambda: self.dual_pane.switch_function_panel_tab("对比"))
        
        compare_menu.addAction(compare_files_action)
        compare_menu.addAction(compare_folders_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.setShortcut("F1")
        about_action.triggered.connect(self.show_about)
        help_action = QAction("帮助文档", self)
        help_action.setShortcut("Ctrl+F1")
        help_action.triggered.connect(self.show_operation_manual)
        
        help_menu.addAction(about_action)
        help_menu.addAction(help_action)
    
    def setup_toolbar(self):
        """
        设置工具栏
        """
        # 创建主工具栏
        self.main_toolbar = QToolBar("主工具栏")
        self.addToolBar(self.main_toolbar)
        
        # 设置工具栏图标大小
        self.main_toolbar.setIconSize(QSize(16, 16))
        
        # 添加导航按钮到工具栏最前方
        # 后退按钮
        self.back_btn = QToolButton()
        self.back_btn.setText("⬅️")
        self.back_btn.setToolTip("后退 (Alt+Left)")
        self.back_btn.clicked.connect(self._on_back_click)
        self.main_toolbar.addWidget(self.back_btn)
        
        # 前进按钮
        self.forward_btn = QToolButton()
        self.forward_btn.setText("➡️")
        self.forward_btn.setToolTip("前进 (Alt+Right)")
        self.forward_btn.clicked.connect(self._on_forward_click)
        self.main_toolbar.addWidget(self.forward_btn)
        
        # 向上按钮
        self.up_btn = QToolButton()
        self.up_btn.setText("⬆️")
        self.up_btn.setToolTip("向上 (Backspace)")
        self.up_btn.clicked.connect(self._on_up_click)
        self.main_toolbar.addWidget(self.up_btn)
        
        # 刷新按钮
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("🔄")
        self.refresh_btn.setToolTip("刷新 (F5)")
        self.refresh_btn.clicked.connect(self._on_refresh_click)
        self.main_toolbar.addWidget(self.refresh_btn)
        
        # 占用空间按钮
        self.disk_space_btn = QToolButton()
        self.disk_space_btn.setText("📊")
        self.disk_space_btn.setToolTip("磁盘空间分析")
        self.disk_space_btn.clicked.connect(self._on_disk_space_click)
        self.main_toolbar.addWidget(self.disk_space_btn)
        
        # 添加分隔符
        self.main_toolbar.addSeparator()
        
        # 添加工具栏按钮
        # 复制
        copy_btn = QToolButton()
        copy_btn.setText("复制")
        copy_btn.setToolTip("复制选中的文件或文件夹 (Ctrl+C)")
        copy_btn.clicked.connect(self.dual_pane.copy_selected_items)
        self.main_toolbar.addWidget(copy_btn)
        
        # 粘贴
        paste_btn = QToolButton()
        paste_btn.setText("粘贴")
        paste_btn.setToolTip("粘贴文件或文件夹 (Ctrl+V)")
        paste_btn.clicked.connect(self.dual_pane.paste_items)
        self.main_toolbar.addWidget(paste_btn)
        
        # 删除
        delete_btn = QToolButton()
        delete_btn.setText("删除")
        delete_btn.setToolTip("删除选中的文件或文件夹 (Del)")
        delete_btn.clicked.connect(self.dual_pane.delete_selected_items)
        self.main_toolbar.addWidget(delete_btn)
        
        # 压缩
        compress_btn = QToolButton()
        compress_btn.setText("压缩")
        compress_btn.setToolTip("压缩选中的文件或文件夹")
        compress_btn.clicked.connect(self.dual_pane.compress_selected_items)
        self.main_toolbar.addWidget(compress_btn)
        
        # 解压
        extract_btn = QToolButton()
        extract_btn.setText("解压")
        extract_btn.setToolTip("解压选中的压缩包")
        extract_btn.clicked.connect(self.dual_pane.decompress_selected_items)
        self.main_toolbar.addWidget(extract_btn)
        
        # 刷新
        refresh_btn = QToolButton()
        refresh_btn.setText("刷新")
        refresh_btn.setToolTip("刷新当前目录 (F5)")
        refresh_btn.clicked.connect(self.dual_pane.refresh)
        self.main_toolbar.addWidget(refresh_btn)
        
        # 添加分隔符
        self.main_toolbar.addSeparator()
        
        # 视图模式下拉框
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["图标", "列表", "详细信息", "缩略图", "平铺"])
        self.view_mode_combo.setToolTip("切换视图模式")
        self.view_mode_combo.setStyleSheet("QComboBox { min-width: 80px; max-width: 80px; }")
        # 为视图模式下拉框添加事件处理
        self.view_mode_combo.currentIndexChanged.connect(self.on_view_mode_combo_changed)
        self.main_toolbar.addWidget(self.view_mode_combo)
        
        # 分组选择下拉框
        self.group_combo = QComboBox()
        self.group_combo.addItems(["无分组", "按类型", "按日期", "按大小"])
        self.group_combo.setToolTip("切换分组方式")
        self.group_combo.setStyleSheet("QComboBox { min-width: 80px; max-width: 80px; }")
        # 为分组下拉框添加事件处理
        self.group_combo.currentIndexChanged.connect(self.on_group_combo_changed)
        self.main_toolbar.addWidget(self.group_combo)
        
        # 添加分隔符
        self.main_toolbar.addSeparator()
        
        # 切换右侧窗格
        self.toggle_right_pane_btn = QToolButton()
        self.toggle_right_pane_btn.setText("显示/隐藏右侧窗格")
        self.toggle_right_pane_btn.setToolTip("切换右侧窗格的显示/隐藏")
        self.toggle_right_pane_btn.clicked.connect(self.dual_pane.toggle_right_pane)
        self.main_toolbar.addWidget(self.toggle_right_pane_btn)
        
        # 切换功能面板
        self.toggle_panel_btn = QToolButton()
        self.toggle_panel_btn.setText("显示/隐藏功能面板")
        self.toggle_panel_btn.setToolTip("切换功能面板的显示/隐藏")
        self.toggle_panel_btn.clicked.connect(self.dual_pane.toggle_function_panel)
        self.main_toolbar.addWidget(self.toggle_panel_btn)
        
        reset_layout_btn = QToolButton()
        reset_layout_btn.setText("恢复默认布局")
        reset_layout_btn.setToolTip("恢复窗口为默认 4:4:3 比例布局")
        reset_layout_btn.clicked.connect(self._reset_layout)
        self.main_toolbar.addWidget(reset_layout_btn)
        
        # 初始化工具栏状态为左窗格的视图和分组模式
        # 获取左窗格的初始视图模式
        left_pane = self.dual_pane.get_left_pane()
        if left_pane:
            # 设置视图模式下拉框
            mode_map = {
                "icon": 0,
                "list": 1,
                "detail": 2,
                "thumbnail": 3,
                "tile": 4
            }
            if left_pane.view_mode in mode_map:
                self.view_mode_combo.setCurrentIndex(mode_map[left_pane.view_mode])
            
            # 设置分组模式下拉框
            group_map = {
                "none": 0,
                "type": 1,
                "date": 2,
                "size": 3
            }
            if left_pane.group_mode in group_map:
                self.group_combo.setCurrentIndex(group_map[left_pane.group_mode])
            
            # 更新菜单选中状态
            self.update_menu_check_states()
    
    def setup_statusbar(self):
        """
        设置状态栏
        """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 左侧窗格信息
        self.left_pane_info = QLabel("左窗: 未选择文件")
        self.status_bar.addWidget(self.left_pane_info, 1)
        
        # 右侧窗格信息
        self.right_pane_info = QLabel("右窗: 未选择文件")
        self.status_bar.addWidget(self.right_pane_info, 1)
        
        # 传输状态
        self.transfer_status = QLabel("传输: 无任务")
        self.status_bar.addWidget(self.transfer_status)
        
        # 系统资源
        self.system_info = QLabel("CPU: 0% | 内存: 0%")
        self.status_bar.addWidget(self.system_info)
        
        # 磁盘空间
        self.disk_space_info = QLabel("磁盘: --/--")
        self.status_bar.addWidget(self.disk_space_info)
        
        # 当前时间
        self.time_info = QLabel("")
        self.status_bar.addWidget(self.time_info)
    
    def setup_theme(self):
        """
        设置主题
        """
        theme = config_manager.get("ui.theme")
        self.change_theme(theme)
    
    def change_theme(self, theme: str):
        """
        切换主题
        
        Args:
            theme: 主题名称，可选值："浅色主题", "深色主题", "系统主题"
        """
        try:
            from config.themes import LIGHT_THEME, DARK_THEME
        except ImportError:
            from src.config.themes import LIGHT_THEME, DARK_THEME
        
        if theme in ["浅色主题", "light"]:
            qss = LIGHT_THEME
            config_manager.set("ui.theme", "light")
            # 更新菜单项选中状态
            self.light_theme_action.setChecked(True)
            self.dark_theme_action.setChecked(False)
            self.system_theme_action.setChecked(False)
        elif theme in ["深色主题", "dark"]:
            qss = DARK_THEME
            config_manager.set("ui.theme", "dark")
            # 更新菜单项选中状态
            self.light_theme_action.setChecked(False)
            self.dark_theme_action.setChecked(True)
            self.system_theme_action.setChecked(False)
        else:  # 系统主题
            # 检测系统主题
            if sys.platform == "win32":
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                       r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    if value == 0:
                        qss = DARK_THEME
                        config_manager.set("ui.theme", "dark")
                    else:
                        qss = LIGHT_THEME
                        config_manager.set("ui.theme", "light")
                except Exception as e:
                    logger.error(f"读取系统主题失败: {e}")
                    qss = LIGHT_THEME
                    config_manager.set("ui.theme", "light")
            else:
                # 默认使用浅色主题
                qss = LIGHT_THEME
                config_manager.set("ui.theme", "light")
            # 更新菜单项选中状态
            self.light_theme_action.setChecked(False)
            self.dark_theme_action.setChecked(False)
            self.system_theme_action.setChecked(True)
        
        QApplication.instance().setStyleSheet(qss)
        
        # 应用主题到Win11地址栏
        theme_name = config_manager.get("ui.theme", "light")
        if hasattr(self, 'dual_pane') and hasattr(self.dual_pane, 'apply_theme'):
            self.dual_pane.apply_theme(theme_name)
        
        logger.info(f"主题已切换为: {theme}")
    
    def setup_timers(self):
        """
        设置定时器
        """
        # 创建系统监控器
        self.system_monitor = SystemMonitor(update_interval=3000, parent=self)
        self.system_monitor.cpu_usage_changed.connect(self._on_cpu_usage_changed)
        self.system_monitor.memory_usage_changed.connect(self._on_memory_usage_changed)
        self.system_monitor.start_monitoring()
        
        # 创建传输监控器
        self.transfer_monitor = TransferMonitor(update_interval=1000, parent=self)
        self.transfer_monitor.transfer_status_changed.connect(self._on_transfer_status_changed)
        self.transfer_monitor.start_monitoring()
        
        # 磁盘空间更新定时器 (5秒)
        self.disk_space_timer = QTimer(self)
        self.disk_space_timer.timeout.connect(self.update_disk_space_info)
        self.disk_space_timer.start(5000)
        
        # 当前时间更新定时器 (1秒)
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time_info)
        self.time_timer.start(1000)
        
        # 初始更新
        self.update_time_info()
        self._update_system_info_display()
        self.update_disk_space_info()
    
    def _on_cpu_usage_changed(self, cpu_percent: float):
        """CPU使用率变化回调"""
        self._current_cpu_percent = cpu_percent
        self._update_system_info_display()
    
    def _on_memory_usage_changed(self, total_gb: float, used_gb: float, percent: float):
        """内存使用率变化回调"""
        self._current_memory_percent = percent
        self._update_system_info_display()
    
    def _on_transfer_status_changed(self, status: str):
        """传输状态变化回调"""
        self.transfer_status.setText(f"传输: {status}")
    
    def _update_system_info_display(self):
        """更新系统信息显示"""
        cpu_percent = getattr(self, '_current_cpu_percent', 0.0)
        memory_percent = getattr(self, '_current_memory_percent', 0.0)
        self.system_info.setText(f"CPU: {cpu_percent:.1f}% | 内存: {memory_percent:.1f}%")
    
    def update_disk_space_info(self):
        """
        更新磁盘空间信息
        """
        try:
            # 获取当前活动窗格的路径
            if hasattr(self, 'dual_pane'):
                active_pane = self.dual_pane.get_active_pane()
                if active_pane:
                    current_path = active_pane.get_current_path()
                    if current_path and os.path.exists(current_path):
                        # 获取磁盘使用情况
                        import psutil
                        disk_usage = psutil.disk_usage(current_path)
                        used_gb = disk_usage.used / (1024 ** 3)
                        total_gb = disk_usage.total / (1024 ** 3)
                        percent = disk_usage.percent
                        
                        # 更新显示
                        self.disk_space_info.setText(f"磁盘: {used_gb:.1f}/{total_gb:.1f}GB ({percent:.0f}%)")
                        return
        
        except Exception as e:
            logger.warning(f"更新磁盘空间信息失败: {e}")
        
        # 如果获取失败，显示默认值
        self.disk_space_info.setText("磁盘: --/--")
    

    def update_time_info(self):
        """
        更新当前时间
        """
        from datetime import datetime
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        # 获取星期几的数字（0-6，0=周一，6=周日）
        weekday_num = now.weekday()
        # 创建中文星期映射
        weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
        # 获取中文星期
        weekday = f"周{weekday_map[weekday_num]}"
        self.time_info.setText(f"{time_str} | {weekday}")
    
    def toggle_hidden_files(self):
        """
        切换显示/隐藏隐藏文件
        """
        show_hidden = self.show_hidden_action.isChecked()
        config_manager.set("ui.show_hidden_files", show_hidden)
        self.dual_pane.set_show_hidden_files(show_hidden)
        logger.info(f"显示隐藏文件: {show_hidden}")
    
    def set_view_mode(self, mode):
        """
        设置视图模式
        
        Args:
            mode: 视图模式
        """
        # 更新配置文件
        config_manager.set("ui.default_view", mode)
        config_manager.save_config()
        
        # 更新双窗格显示
        self.dual_pane.set_view_mode(mode)
        
        # 更新视图模式下拉框选择
        mode_map = {
            "icon": 0,
            "list": 1,
            "detail": 2,
            "thumbnail": 3,
            "tile": 4
        }
        if mode in mode_map:
            self.view_mode_combo.setCurrentIndex(mode_map[mode])
        
        # 更新菜单勾选状态
        self.update_menu_check_states()
    
    def set_group_mode(self, mode):
        """
        设置分组模式
        
        Args:
            mode: 分组模式
        """
        # 更新配置文件
        config_manager.set("ui.default_group", mode)
        config_manager.save_config()
        
        # 更新双窗格显示
        self.dual_pane.set_group_mode(mode)
        
        # 更新分组下拉框选择
        group_map = {
            "none": 0,
            "type": 1,
            "date": 2,
            "size": 3
        }
        if mode in group_map:
            self.group_combo.setCurrentIndex(group_map[mode])
        
        # 更新菜单勾选状态
        self.update_menu_check_states()
    
    def update_menu_check_states(self):
        """
        更新菜单的勾选状态
        """
        # 获取当前视图模式和分组模式
        current_view_mode = config_manager.get("ui.default_view")
        current_group_mode = config_manager.get("ui.default_group", "none")
        
        # 更新视图模式菜单勾选状态
        self.icon_view_action.setChecked(current_view_mode == "icon")
        self.list_view_action.setChecked(current_view_mode == "list")
        self.detail_view_action.setChecked(current_view_mode == "detail")
        self.thumbnail_view_action.setChecked(current_view_mode == "thumbnail")
        self.tile_view_action.setChecked(current_view_mode == "tile")
        
        # 更新分组菜单勾选状态
        self.no_group_action.setChecked(current_group_mode == "none")
        self.group_by_type_action.setChecked(current_group_mode == "type")
        self.group_by_date_action.setChecked(current_group_mode == "date")
        self.group_by_size_action.setChecked(current_group_mode == "size")
    
    def on_view_mode_combo_changed(self, index):
        """
        视图模式下拉框变化事件处理
        """
        mode_map = [
            "icon",
            "list",
            "detail",
            "thumbnail",
            "tile"
        ]
        if 0 <= index < len(mode_map):
            self.set_view_mode(mode_map[index])
    
    def on_group_combo_changed(self, index):
        """
        分组下拉框变化事件处理
        """
        group_map = [
            "none",
            "type",
            "date",
            "size"
        ]
        if 0 <= index < len(group_map):
            self.set_group_mode(group_map[index])
    
    def show_settings_dialog(self):
        """
        显示设置对话框
        """
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        # 连接设置更改信号
        dialog.settings_changed.connect(self.on_settings_changed)
        
        # 显示对话框
        dialog.exec()
    
    def on_settings_changed(self):
        """
        设置更改事件处理
        """
        # 更新文件列表的字体和字号
        self.dual_pane.update_file_list_font()
        
        # 更新同步窗格设置
        sync_panes = config_manager.get("ui.sync_panes", True)
        self.dual_pane.update_sync_panes_setting(sync_panes)
        
        logger.info("设置已更新")
    
    def show_operation_manual(self):
        """
        显示操作说明
        """
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QPushButton, QHBoxLayout, QScrollArea
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QTextOption
        import os
        import sys
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("操作说明")
        dialog.resize(800, 600)
        
        # 创建布局
        main_layout = QVBoxLayout(dialog)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建文本编辑框
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        text_edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        
        # 读取README.md文件内容
        # 尝试多种路径获取方式
        readme_path = None
        
        # 方式1：使用__file__获取项目根目录
        try:
            readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "README.md")
            if os.path.exists(readme_path):
                pass
            else:
                # 方式2：使用当前工作目录
                readme_path = os.path.join(os.getcwd(), "README.md")
                if not os.path.exists(readme_path):
                    # 方式3：对于打包后的可执行文件，检查sys._MEIPASS
                    if hasattr(sys, '_MEIPASS'):
                        readme_path = os.path.join(sys._MEIPASS, "README.md")
        except Exception as e:
            logger.error(f"获取README.md路径失败: {e}")
        
        try:
            if readme_path and os.path.exists(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    text_edit.setPlainText(content)
            else:
                # 如果无法找到README.md文件，显示提示信息
                text_edit.setPlainText("无法找到README.md文件\n\n请确保README.md文件与可执行文件在同一目录下。")
                logger.error(f"README.md文件不存在: {readme_path}")
        except Exception as e:
            text_edit.setPlainText(f"无法读取README.md文件: {str(e)}")
            logger.error(f"读取README.md文件失败: {e}")
        
        scroll_area.setWidget(text_edit)
        main_layout.addWidget(scroll_area)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 创建关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec()
    
    def show_about(self):
        """
        显示关于对话框
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        from PySide6.QtCore import Qt
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("关于 AFM-EST")
        dialog.resize(400, 300)
        
        # 创建布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 显示应用程序名称
        title_label = QLabel("AFM-EST")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 显示版本号
        version_label = QLabel("版本 1.1.0")
        version_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(version_label)
        
        # 显示软件简介
        desc_label = QLabel("全能资源搜索管理器\n\nAdvanced File Manager with Enhanced Search & Transfer")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # 显示版权信息
        copyright_label = QLabel("© 2026 AFM-EST Team")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("font-size: 12px; color: #666;")
        main_layout.addWidget(copyright_label)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 创建关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec()
    
    def _check_and_resume_whoosh_index(self):
        from services.unified_search_service import unified_search_service
        
        ntfs_built = unified_search_service.fast_search.index_built
        whoosh_built = unified_search_service.fulltext_search.index_built
        whoosh_indexing = unified_search_service.fulltext_search.is_indexing
        
        if ntfs_built and not whoosh_built and not whoosh_indexing:
            logger.info("[MainWindow] NTFS索引已存在，Whoosh索引未完成，自动恢复后台构建")
            if hasattr(self, 'dual_pane') and hasattr(self.dual_pane, 'function_panel'):
                self.dual_pane.function_panel._start_whoosh_background()
    
    def _reset_layout(self):
        if hasattr(self, 'dual_pane'):
            self.dual_pane.reset_layout()
            from core.config import config_manager
            config_manager.set("ui.splitter_ratio", [4/11, 4/11, 3/11])
    
    def build_search_index(self):
        """创建搜索索引"""
        from PySide6.QtWidgets import QMessageBox
        from services.unified_search_service import unified_search_service
        
        fast_search_built = unified_search_service.fast_search.index_built
        fulltext_search_built = unified_search_service.fulltext_search.index_built
        
        if fast_search_built and fulltext_search_built:
            reply = QMessageBox.question(
                self,
                "搜索索引",
                "搜索索引已存在。\n\n是否重新构建索引？\n（这将删除现有索引并重新构建）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        elif fast_search_built and not fulltext_search_built:
            whoosh_indexing = unified_search_service.fulltext_search.is_indexing
            if whoosh_indexing:
                QMessageBox.information(
                    self, "搜索索引",
                    "全文索引正在后台构建中，请等待完成。\n\n进度显示在状态栏。"
                )
                return
            reply = QMessageBox.question(
                self,
                "搜索索引",
                "快速搜索索引已存在，但全文搜索索引尚未构建。\n\n是否现在构建全文搜索索引？\n（将在后台构建，不影响正常使用）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.No:
                return
            
            if hasattr(self, 'dual_pane') and hasattr(self.dual_pane, 'function_panel'):
                self.dual_pane.function_panel._start_whoosh_background()
            return
        
        # 调用function_panel的索引构建方法
        if hasattr(self, 'dual_pane') and hasattr(self.dual_pane, 'function_panel'):
            self.dual_pane.function_panel._build_search_index_with_progress()
        else:
            QMessageBox.warning(self, "错误", "无法访问功能面板")
    
    def clear_search_index(self):
        """清除已创建的搜索索引"""
        import os
        from PySide6.QtWidgets import QMessageBox
        from services.unified_search_service import unified_search_service
        from services.index_location_manager import IndexLocationManager
        
        whoosh_index_dir = unified_search_service.fulltext_search.index_dir
        whoosh_index_path = os.path.abspath(whoosh_index_dir)
        
        location_manager = IndexLocationManager()
        appdata_index_path = location_manager.get_default_location()
        
        config_files = []
        for cfg in ["config/index_data.json", "config/index_status.json", "config/whoosh_index_status.json"]:
            if os.path.exists(cfg):
                config_files.append(os.path.abspath(cfg))
        
        message = f"确定要清除所有已创建的搜索索引吗？\n\n这将删除以下内容：\n"
        message += f"- Whoosh全文索引: {whoosh_index_path}\n"
        message += f"- 备用索引目录: {appdata_index_path}\n"
        
        if config_files:
            for cfg in config_files:
                message += f"- 配置文件: {cfg}\n"
        else:
            message += "- 索引状态配置文件\n"
        
        message += "\n清除后需要重新构建索引才能使用搜索功能。"
        
        reply = QMessageBox.question(
            self,
            "清除搜索索引",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                unified_search_service.clear_all_indexes()
                QMessageBox.information(
                    self,
                    "清除成功",
                    "所有搜索索引已成功清除。\n\n下次使用搜索功能时需要重新构建索引。"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "清除失败",
                    f"清除索引时发生错误：\n{e}"
                )
    
    def open_index_folder(self):
        """打开索引文件夹"""
        import os
        import subprocess
        from PySide6.QtWidgets import QMessageBox
        from services.unified_search_service import unified_search_service
        
        whoosh_index_dir = unified_search_service.fulltext_search.index_dir
        whoosh_index_path = os.path.abspath(whoosh_index_dir)
        
        has_whoosh = os.path.exists(whoosh_index_path)
        has_fast_search = os.path.exists("config/index_data.db")
        
        if has_whoosh:
            try:
                if os.name == 'nt':
                    os.startfile(whoosh_index_path)
                else:
                    subprocess.run(['open', whoosh_index_path])
            except Exception as e:
                QMessageBox.warning(self, "打开失败", f"无法打开索引文件夹：\n{e}")
        elif has_fast_search:
            fast_search_path = os.path.abspath("config/index_data.db")
            reply = QMessageBox.question(
                self,
                "索引类型",
                f"全文索引文件夹不存在，但快速搜索索引(SQLite)已存在。\n\n快速搜索索引位置: {fast_search_path}\n\n是否打开快速搜索索引所在目录？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                try:
                    if os.name == 'nt':
                        os.startfile(os.path.dirname(fast_search_path))
                    else:
                        subprocess.run(['open', os.path.dirname(fast_search_path)])
                except Exception as e:
                    QMessageBox.warning(self, "打开失败", f"无法打开索引文件夹：\n{e}")
        else:
            QMessageBox.information(self, "索引不存在", "索引文件夹不存在，请先创建搜索索引。")
    
    def closeEvent(self, event):
        """
        关闭事件处理
        
        Args:
            event: 关闭事件对象
        """
        # 停止系统监控
        if hasattr(self, 'system_monitor'):
            self.system_monitor.stop_monitoring()
        
        # 停止传输监控
        if hasattr(self, 'transfer_monitor'):
            self.transfer_monitor.stop_monitoring()
        
        # 保存窗口大小
        config_manager.set("ui.window_size", [self.width(), self.height()])
        # 保存分隔器比例
        splitter_ratio = self.dual_pane.get_splitter_ratio()
        config_manager.set("ui.splitter_ratio", splitter_ratio)
        
        # 保存功能面板可见状态
        config_manager.set("ui.function_panel_visible", self.dual_pane.function_panel.isVisible())
        
        # 保存左右窗格路径（如果设置了记住路径）
        remember_last_path = config_manager.get("ui.remember_last_path", True)
        if remember_last_path:
            # 获取左右窗格的当前路径
            left_path = self.dual_pane.get_left_pane().get_current_path()
            right_path = self.dual_pane.get_right_pane().get_current_path()
            config_manager.set("ui.left_pane_path", left_path)
            config_manager.set("ui.right_pane_path", right_path)
            logger.info(f"保存左右窗格路径: {left_path}, {right_path}")
        
        # 保存配置到文件
        config_manager.save_config()
        
        logger.info("主窗口已关闭")
        event.accept()
    
    def _on_back_click(self):
        """后退按钮点击"""
        active_pane = self.dual_pane.get_active_pane()
        if active_pane and hasattr(active_pane, '_on_back_click'):
            active_pane._on_back_click()
    
    def _on_forward_click(self):
        """前进按钮点击"""
        active_pane = self.dual_pane.get_active_pane()
        if active_pane and hasattr(active_pane, '_on_forward_click'):
            active_pane._on_forward_click()
    
    def _on_up_click(self):
        """向上按钮点击"""
        active_pane = self.dual_pane.get_active_pane()
        if active_pane and hasattr(active_pane, '_on_up_click'):
            active_pane._on_up_click()
    
    def _on_refresh_click(self):
        """刷新按钮点击"""
        active_pane = self.dual_pane.get_active_pane()
        if active_pane and hasattr(active_pane, 'refresh'):
            active_pane.refresh()
    
    def _on_disk_space_click(self):
        """占用空间按钮点击"""
        from ui.disk_space_dialog import DiskSpaceDialog
        
        current_path = ""
        active_pane = self.dual_pane.get_active_pane()
        if active_pane and hasattr(active_pane, 'current_path'):
            current_path = active_pane.current_path
        
        dialog = DiskSpaceDialog(current_path, self)
        dialog.exec()

