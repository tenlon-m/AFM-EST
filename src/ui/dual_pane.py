#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双窗格组件模块
实现左右两个文件浏览窗口
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, 
    QLineEdit, QListView, QFileSystemModel, 
    QTreeView, QAbstractItemView, QMenu, QDialog,
    QLabel, QPushButton
)
from core.utils import show_warning, show_info, show_question
from ui.function_panel import FunctionPanel
from ui.disk_selector.disk_selector import DiskSelector
from PySide6.QtCore import Qt, QSize, QUrl, QDir, QSortFilterProxyModel, Signal
from PySide6.QtGui import QAction
import os
import threading
from core.logger import logger
from core.config import config_manager
from core.utils import format_size, detect_file_encoding, format_time, get_folder_size, get_unique_path

class ChineseHeaderProxyModel(QSortFilterProxyModel):
    """
    自定义代理模型，用于将文件列表标题转换为中文
    """
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        重写headerData方法，返回中文标题
        
        Args:
            section: 列索引
            orientation: 方向
            role: 数据角色
            
        Returns:
            中文标题
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            # 返回中文标题
            chinese_headers = ["名称", "大小", "类型", "修改日期"]
            if 0 <= section < len(chinese_headers):
                return chinese_headers[section]
        return super().headerData(section, orientation, role)

class PaneWidget(QWidget):
    """
    单个窗格组件
    包含地址栏、导航按钮和文件列表
    """
    items_info_ready = Signal(dict)

    def __init__(self, parent=None, pane_type="left"):
        """
        初始化单个窗格
        
        Args:
            parent: 父组件
            pane_type: 窗格类型，"left"或"right"
        """
        super().__init__(parent)
        self.pane_type = pane_type
        self.current_path = ""
        self.show_hidden_files = config_manager.get("ui.show_hidden_files")
        # 初始化视图模式和分组模式
        self.view_mode = config_manager.get("ui.default_view")
        self.group_mode = config_manager.get("ui.default_group", "none")
        # 初始化路径历史记录
        self.path_history = []
        self.history_index = -1
        # 剪贴板数据现在由父组件DualPane管理，实现跨窗格共享
        self.init_ui()
        
        # 初始化字体设置
        self.update_file_list_font()
        
        # 延迟调整列宽，确保窗格已完全显示
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._adjust_column_widths())
        
    def init_ui(self):
        """
        初始化窗格UI组件
        """
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建顶部导航栏
        nav_bar = QFrame()
        nav_bar.setFrameShape(QFrame.NoFrame)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(4, 0, 4, 0)
        nav_layout.setSpacing(4)
        
        # 创建Windows 11风格地址栏（集成磁盘选择器）
        from ui.address_bar.win11_address_bar import Win11AddressBar
        self.win11_address_bar = Win11AddressBar()
        self.win11_address_bar.path_changed.connect(self._on_path_changed)
        nav_layout.addWidget(self.win11_address_bar, 1)
        
        # 保留旧的地址栏引用（用于兼容性）
        self.address_bar = QLineEdit()
        self.address_bar.setVisible(False)  # 隐藏旧地址栏
        
        # 保留旧的磁盘选择器引用（用于兼容性）
        self.disk_selector = DiskSelector()
        self.disk_selector.setVisible(False)  # 隐藏旧磁盘选择器
        
        # 保留导航按钮引用（用于兼容性，实际按钮在工具栏）
        self.back_btn = None
        self.forward_btn = None
        self.up_btn = None
        self.refresh_btn = None
        
        # 设置导航栏样式
        nav_bar.setStyleSheet("""
            QFrame {
                background-color: #F8F8F8;
                border: none;
                border-bottom: 1px solid #E5E5E5;
                max-height: 30px;
            }
        """)
        nav_bar.setFixedHeight(30)
        
        main_layout.addWidget(nav_bar)
        
        # 创建文件列表视图
        self.view_mode = config_manager.get("ui.default_view")
        
        # 创建文件系统模型
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.model.setRootPath("")
        
        # 创建中文标题代理模型
        self.proxy_model = ChineseHeaderProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        # 创建视图
        if self.view_mode == "detail":
            self.file_view = QTreeView()
            self.file_view.setRootIsDecorated(True)
            self.file_view.setItemsExpandable(True)
            self.file_view.setAlternatingRowColors(True)
            self.file_view.setAllColumnsShowFocus(True)
            self.file_view.setSortingEnabled(True)
            self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
            # 设置默认按名称升序排序
            self.file_view.sortByColumn(0, Qt.AscendingOrder)
        else:
            self.file_view = QListView()
            self.file_view.setViewMode(QListView.IconMode)
            self.file_view.setIconSize(QSize(64, 64))
            self.file_view.setUniformItemSizes(True)
            self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # 设置焦点策略，确保可以接收焦点
        self.file_view.setFocusPolicy(Qt.StrongFocus)
        
        # 使用代理模型来显示中文标题
        self.file_view.setModel(self.proxy_model)
        
        # 设置列宽（在设置模型后执行）
        if self.view_mode == "detail":
            for column in range(self.model.columnCount()):
                self.file_view.resizeColumnToContents(column)
        
        # 连接选择变化事件（必须在设置模型之后）
        self.file_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        main_layout.addWidget(self.file_view)
        
        # 连接双击事件
        self.file_view.doubleClicked.connect(self._on_double_click)
        
        # 连接右键菜单事件
        self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # 启用拖放功能
        self.file_view.setDragEnabled(True)
        self.file_view.setAcceptDrops(True)
        self.file_view.setDropIndicatorShown(True)
        self.file_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.file_view.setDefaultDropAction(Qt.CopyAction)
        self.file_view.setDragDropOverwriteMode(False)
        
        # 连接拖放事件
        self.file_view.dragEnterEvent = self._drag_enter_event
        self.file_view.dragMoveEvent = self._drag_move_event
        self.file_view.dropEvent = self._drop_event
        self.file_view.startDrag = self._start_drag
        
        # 连接焦点事件
        self.file_view.focusInEvent = self._on_focus_in
        self.file_view.focusOutEvent = self._on_focus_out
        self.focusInEvent = self._on_focus_in
        self.focusOutEvent = self._on_focus_out
        # 为地址栏添加焦点事件
        self.address_bar.focusInEvent = self._on_focus_in
        self.address_bar.focusOutEvent = self._on_focus_out
        
        # 初始化焦点样式（左窗格有焦点，右窗格无焦点）
        # 注意：不在这里设置初始路径，由主窗口负责设置
        # 这样可以避免焦点样式被覆盖
    


    def set_current_path(self, path):
        """
        设置当前路径
        
        Args:
            path: 要设置的路径
        """
        # 验证和清理路径
        if not path:
            logger.error(f"无效路径: {path}")
            return
            
        # 规范化路径格式
        normalized_path = path.strip()
        
        final_path = ""
        
        # 处理Windows路径格式
        if os.name == 'nt':
            # 处理各种可能的路径格式，如 "C:", "C:/", "C:\", "D::\", ":"
            
            # 移除多余的冒号
            if normalized_path.count(':') > 1:
                # 只保留第一个冒号
                first_colon = normalized_path.find(':')
                normalized_path = normalized_path[:first_colon+1] + normalized_path[first_colon+1:].replace(':', '')
            
            # 查找冒号的位置
            colon_pos = normalized_path.find(':')
            
            # 有效的Windows驱动器格式必须是 "X:" 或 "X:xxx"
            if colon_pos == 1 and len(normalized_path) >= 2:
                # 提取驱动器字母
                drive_letter = normalized_path[0].upper()
                
                # 如果只有驱动器号（如 "C:"），则添加反斜杠
                if len(normalized_path) == 2:
                    final_path = f"{drive_letter}:\\"
                else:
                    # 保留完整路径，替换斜杠为反斜杠
                    final_path = normalized_path.replace('/', '\\')
            else:
                # 尝试从地址栏输入中提取有效的驱动器格式
                if len(normalized_path) >= 1 and normalized_path[0].isalpha():
                    drive_letter = normalized_path[0].upper()
                    final_path = f"{drive_letter}:\\"
                else:
                    logger.error(f"无效的Windows路径格式: {path}")
                    return
        else:
            # Linux/macOS路径格式
            final_path = normalized_path
        
        if final_path != self.current_path:
            # 添加到路径历史记录
            self._add_to_history(final_path)
            
            self.current_path = final_path
        
        # 更新地址栏显示
        self.address_bar.setText(final_path)
        
        # 更新Win11地址栏
        if hasattr(self, 'win11_address_bar'):
            self.win11_address_bar.set_path(final_path)
        
        # 更新磁盘选择按钮文本
        if os.name == 'nt' and len(final_path) >= 2:
            drive_letter = final_path[0].upper() + ':'
            # 查找对应的磁盘信息并更新按钮
            if hasattr(self, 'disk_selector') and self.disk_selector._disks:
                for disk in self.disk_selector._disks:
                    if disk.drive_letter == drive_letter:
                        self.disk_selector._set_current_disk(disk)
                        break
        
        # 设置文件视图根路径
        root_index = self.model.setRootPath(final_path)
        # 将源模型的索引转换为代理模型的索引
        proxy_index = self.proxy_model.mapFromSource(root_index)
        self.file_view.setRootIndex(proxy_index)
        
        # 延迟调整列宽，确保模型已加载数据且窗格已完全显示
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._adjust_column_widths())
        
        logger.info(f"{self.pane_type}窗格路径已切换到: {final_path}")
    
    def _on_disk_selected(self, disk_info):
        """
        处理磁盘选择事件
        
        Args:
            disk_info: 磁盘信息对象
        """
        if disk_info and hasattr(disk_info, 'path'):
            self.set_current_path(disk_info.path)
    
    def get_current_path(self):
        """
        获取当前路径
        
        Returns:
            当前路径
        """
        return self.current_path
    
    def go_to_path(self):
        """
        跳转到地址栏输入的路径
        """
        path = self.address_bar.text().strip()
        if path:
            self.set_current_path(path)
    
    def _address_bar_mouse_press(self, event):
        """
        处理地址栏鼠标点击事件，点击时全选文本
        
        Args:
            event: 鼠标事件
        """
        # 调用原始的mousePressEvent
        QLineEdit.mousePressEvent(self.address_bar, event)
        
        # 如果是左键点击，全选文本
        if event.button() == Qt.LeftButton:
            self.address_bar.selectAll()
    
    def refresh(self):
        """
        刷新当前目录
        """
        # 强制刷新QFileSystemModel缓存
        self.model.setRootPath("")
        
        # 重新设置当前路径
        root_index = self.model.setRootPath(self.current_path)
        # 将源模型的索引转换为代理模型的索引
        proxy_index = self.proxy_model.mapFromSource(root_index)
        # 设置视图的根索引,保持当前路径
        self.file_view.setRootIndex(proxy_index)
        
        # 延迟调整列宽，确保模型已加载数据且窗格已完全显示
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._adjust_column_widths())
        
        self.update_drive_list()
        logger.info(f"{self.pane_type}窗格已刷新")
    
    def update_drive_list(self):
        """更新磁盘列表"""
        try:
            if hasattr(self, 'disk_selector') and self.disk_selector:
                self.disk_selector.refresh_disks()
        except Exception as e:
            logger.debug(f"更新磁盘列表失败: {e}")
    
    def _add_to_history(self, path):
        """
        添加路径到历史记录
        
        Args:
            path: 要添加的路径
        """
        # 如果当前不在历史记录末尾，截断历史记录
        if self.history_index < len(self.path_history) - 1:
            self.path_history = self.path_history[:self.history_index + 1]
        
        # 添加新路径到历史记录
        self.path_history.append(path)
        self.history_index = len(self.path_history) - 1
        
        # 更新导航按钮状态
        self._update_nav_buttons()
    
    def _on_path_changed(self, path: str):
        """
        处理Win11AddressBar路径变更事件
        
        Args:
            path: 新路径
        """
        if not path:
            # 空路径表示显示所有磁盘
            self.current_path = ""
            self.address_bar.setText("所有磁盘")
            if hasattr(self, 'win11_address_bar'):
                # 清空Win11地址栏的路径显示
                pass
            # 设置文件视图根路径为空，显示所有磁盘
            root_index = self.model.setRootPath("")
            proxy_index = self.proxy_model.mapFromSource(root_index)
            self.file_view.setRootIndex(proxy_index)
        else:
            self.set_current_path(path)
    
    def _update_nav_buttons(self):
        """
        更新导航按钮的状态（启用/禁用）
        """
        # 导航按钮已移到主窗口工具栏，这里不再更新
        # 如果按钮存在（兼容性），则更新状态
        if self.back_btn:
            self.back_btn.setEnabled(self.history_index > 0)
        
        if self.forward_btn:
            self.forward_btn.setEnabled(self.history_index < len(self.path_history) - 1)
    
    def _on_back_click(self):
        """
        处理后退按钮点击
        """
        if self.history_index > 0:
            self.history_index -= 1
            previous_path = self.path_history[self.history_index]
            self.current_path = previous_path
            self.address_bar.setText(previous_path)
            if hasattr(self, 'win11_address_bar') and self.win11_address_bar:
                self.win11_address_bar.set_path(previous_path)
            
            root_index = self.model.setRootPath(previous_path)
            proxy_index = self.proxy_model.mapFromSource(root_index)
            self.file_view.setRootIndex(proxy_index)
            
            if os.name == 'nt':
                drive = previous_path[:2]
            else:
                drive = previous_path

            
            logger.info(f"{self.pane_type}窗格已后退到: {previous_path}")
            
            self._update_nav_buttons()
    
    def _on_forward_click(self):
        """
        处理前进按钮点击
        """
        if self.history_index < len(self.path_history) - 1:
            self.history_index += 1
            next_path = self.path_history[self.history_index]
            self.current_path = next_path
            self.address_bar.setText(next_path)
            if hasattr(self, 'win11_address_bar') and self.win11_address_bar:
                self.win11_address_bar.set_path(next_path)
            
            root_index = self.model.setRootPath(next_path)
            proxy_index = self.proxy_model.mapFromSource(root_index)
            self.file_view.setRootIndex(proxy_index)
            
            if os.name == 'nt':
                drive = next_path[:2]
            else:
                drive = next_path

            
            logger.info(f"{self.pane_type}窗格已前进到: {next_path}")
            
            self._update_nav_buttons()
    
    def _on_up_click(self):
        """
        处理向上按钮点击
        """
        # 处理当前路径是根目录的情况
        if os.name == 'nt':
            # Windows根目录格式：X:\
            if len(self.current_path) <= 3:
                # 在根目录时，点击向上按钮显示所有磁盘列表
                # 设置当前路径为空，以便显示所有磁盘
                self.current_path = ""
                self.address_bar.setText("所有磁盘")
                # 设置文件视图根路径为空，显示所有磁盘
                root_index = self.model.setRootPath("")
                proxy_index = self.proxy_model.mapFromSource(root_index)
                self.file_view.setRootIndex(proxy_index)

                return
        else:
            # Linux/macOS根目录格式：/
            if self.current_path == '/':
                return
        
        # 获取父目录路径
        parent_path = os.path.dirname(self.current_path)
        
        # 切换到父目录
        self.set_current_path(parent_path)
    
    def set_show_hidden_files(self, show_hidden):
        """
        设置是否显示隐藏文件
        
        Args:
            show_hidden: 是否显示隐藏文件
        """
        self.show_hidden_files = show_hidden
        if show_hidden:
            self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        else:
            self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self.refresh()
    
    def get_selected_items(self):
        """
        获取选中的文件/文件夹列表
        
        Returns:
            选中的文件/文件夹列表，每个元素包含name、path、type等信息
        """
        selected_indexes = self.file_view.selectedIndexes()
        selected_items = []
        
        # 去重处理（QTreeView会返回所有列的索引）
        processed_paths = set()
        
        for index in selected_indexes:
            if index.column() == 0:  # 只处理文件名列
                # 将代理模型的索引转换为源模型的索引
                source_index = self.proxy_model.mapToSource(index)
                if source_index.isValid():
                    file_path = self.model.filePath(source_index)
                    if file_path not in processed_paths:
                        processed_paths.add(file_path)
                        file_name = self.model.fileName(source_index)
                        file_type = "文件夹" if self.model.isDir(source_index) else "文件"
                        selected_items.append({
                            "name": file_name,
                            "path": file_path,
                            "type": file_type,
                            "is_dir": self.model.isDir(source_index)
                        })
        
        return selected_items
    
    def _on_double_click(self, index):
        """
        处理文件/文件夹双击事件
        
        Args:
            index: 双击的索引（代理模型的索引）
        """
        if not index.isValid():
            return
        
        # 将代理模型的索引转换为源模型的索引
        source_index = self.proxy_model.mapToSource(index)
        file_path = self.model.filePath(source_index)
        
        if self.model.isDir(source_index):
            # 双击文件夹，进入该文件夹
            self.set_current_path(file_path)
        else:
            # 双击文件，打开文件
            self._open_file(file_path)
    
    def _open_file(self, file_path):
        """
        打开文件
        
        Args:
            file_path: 要打开的文件路径
        """
        import os
        import subprocess
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
    
    def _open_with(self, file_path):
        """
        打开方式对话框
        
        Args:
            file_path: 要打开的文件路径
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os
        import subprocess
        
        try:
            if os.name == 'nt':  # Windows
                # 使用Windows的"打开方式"对话框
                import ctypes
                ctypes.windll.shell32.OpenAs_RunDLL(0, 0, file_path, 0)
            else:  # Linux/macOS
                # 让用户选择程序
                program, _ = QFileDialog.getOpenFileName(
                    self, 
                    "选择程序", 
                    "", 
                    "可执行文件 (*.sh *.bin *.app *);;所有文件 (*)"
                )
                if program:
                    subprocess.call([program, file_path])
            logger.info(f"使用自定义程序打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开方式失败: {file_path}, 错误: {e}")
            QMessageBox.warning(self, "错误", f"无法打开文件: {str(e)}")
    
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 右键点击的位置
        """
        # 获取点击位置对应的文件索引（代理模型的索引）
        index = self.file_view.indexAt(pos)
        selected_items = self.get_selected_items()
        
        # 创建菜单
        menu = QMenu(self)
        
        # 如果点击了有效文件/文件夹
        if index.isValid():
            # 将代理模型的索引转换为源模型的索引
            source_index = self.proxy_model.mapToSource(index)
            file_path = self.model.filePath(source_index)
            is_dir = self.model.isDir(source_index)
            
            # 基础操作
            open_action = menu.addAction("打开")
            open_action.triggered.connect(lambda: self._open_file(file_path))
            
            # 只有文件才显示"打开方式"
            if not is_dir:
                open_with_action = menu.addAction("打开方式")
                open_with_action.triggered.connect(lambda: self._open_with(file_path))
            
            menu.addSeparator()
            
            # 剪切复制粘贴
            cut_action = menu.addAction("剪切")
            cut_action.setShortcut("Ctrl+X")
            cut_action.triggered.connect(self.cut_selected_items)
            
            copy_action = menu.addAction("复制")
            copy_action.setShortcut("Ctrl+C")
            copy_action.triggered.connect(self.copy_selected_items)
            
            paste_action = menu.addAction("粘贴")
            paste_action.setShortcut("Ctrl+V")
            paste_action.triggered.connect(self.paste_items)
            
            menu.addSeparator()
            
            # 删除和重命名
            delete_action = menu.addAction("删除")
            delete_action.setShortcut("Delete")
            delete_action.triggered.connect(self.delete_selected_items)
            
            # 只有选中单个文件/文件夹时才显示"重命名"
            if len(selected_items) == 1:
                rename_action = menu.addAction("重命名")
                rename_action.setShortcut("F2")
                rename_action.triggered.connect(self._on_rename_clicked)
            
            menu.addSeparator()
            
            # 新建操作
            new_folder_action = menu.addAction("新建文件夹")
            new_folder_action.setShortcut("Ctrl+Shift+N")
            new_folder_action.triggered.connect(self.create_new_folder)
            
            new_file_action = menu.addAction("新建文件")
            new_file_action.setShortcut("Ctrl+N")
            new_file_action.triggered.connect(self.create_new_file)
            
            menu.addSeparator()
            
            # 文件操作功能
            copy_name_action = menu.addAction("复制文件名")
            copy_name_action.triggered.connect(lambda: self._copy_file_name(file_path))
            
            copy_path_action = menu.addAction("复制文件路径")
            copy_path_action.triggered.connect(lambda: self._copy_file_path(file_path))
            
            open_folder_action = menu.addAction("打开所在文件夹")
            open_folder_action.triggered.connect(lambda: self._open_parent_folder(file_path))
            
            menu.addSeparator()
            
            # 高级功能
            if not is_dir:
                # 预览子菜单
                preview_menu = QMenu("预览", self)
                quick_preview_action = preview_menu.addAction("快速预览")
                quick_preview_action.triggered.connect(lambda: self._preview_file(file_path))
                preview_menu.addSeparator()
                preview_in_new_window = preview_menu.addAction("在新窗口预览")
                preview_in_new_window.triggered.connect(lambda: self._preview_in_new_window(file_path))
                menu.addMenu(preview_menu)
                
                verify_action = menu.addAction("文件校验")
                verify_action.triggered.connect(lambda: self._verify_file(file_path))
                
                # 添加到对比子菜单
                compare_menu = QMenu("添加到对比", self)
                compare_to_file1_action = compare_menu.addAction("添加到文件一")
                compare_to_file1_action.triggered.connect(lambda: self._add_to_compare(file_path, 1))
                compare_to_file2_action = compare_menu.addAction("添加到文件二")
                compare_to_file2_action.triggered.connect(lambda: self._add_to_compare(file_path, 2))
                menu.addMenu(compare_menu)
            else:
                # 文件夹也可以添加到对比
                compare_menu = QMenu("添加到对比", self)
                compare_to_file1_action = compare_menu.addAction("添加到第一路径")
                compare_to_file1_action.triggered.connect(lambda: self._add_to_compare(file_path, 1))
                compare_to_file2_action = compare_menu.addAction("添加到第二路径")
                compare_to_file2_action.triggered.connect(lambda: self._add_to_compare(file_path, 2))
                menu.addMenu(compare_menu)
            
            # 压缩解压
            if is_dir:
                compress_action = menu.addAction("压缩到...")
                compress_action.triggered.connect(lambda: self._compress_items([file_path]))
            else:
                # 检查是否为压缩文件
                _, ext = os.path.splitext(file_path)
                if ext.lower() in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2', '.tar.xz']:
                    decompress_action = menu.addAction("解压到...")
                    decompress_action.triggered.connect(lambda: self._decompress_file(file_path))
            
            # 发送到功能（仅Windows）
            if os.name == 'nt' and not is_dir:
                send_to_targets = self._get_send_to_targets()
                if send_to_targets:
                    send_to_menu = QMenu("发送到", self)
                    for target_name, target_path in send_to_targets:
                        target_action = send_to_menu.addAction(target_name)
                        target_action.triggered.connect(lambda checked, t=target_path, f=file_path: self._send_to_target(f, t))
                    menu.addMenu(send_to_menu)
            
            menu.addSeparator()
            
            # 只有选中单个文件/文件夹时才显示"属性"
            if len(selected_items) == 1:
                properties_action = menu.addAction("属性")
                properties_action.setShortcut("Alt+Enter")
                properties_action.triggered.connect(self._on_properties_clicked)
        else:
            # 空白处右键菜单
            new_folder_action = menu.addAction("新建文件夹")
            new_folder_action.setShortcut("Ctrl+Shift+N")
            new_folder_action.triggered.connect(self.create_new_folder)
            
            new_file_action = menu.addAction("新建文件")
            new_file_action.setShortcut("Ctrl+N")
            new_file_action.triggered.connect(self.create_new_file)
            
            menu.addSeparator()
            
            paste_action = menu.addAction("粘贴")
            paste_action.setShortcut("Ctrl+V")
            paste_action.triggered.connect(self.paste_items)
            
            menu.addSeparator()
            
            # 显示隐藏文件选项
            from PySide6.QtWidgets import QAction
            show_hidden_action = QAction("显示隐藏文件", self)
            show_hidden_action.setCheckable(True)
            show_hidden_action.setShortcut("Ctrl+H")
            # 从配置读取当前状态
            show_hidden = config_manager.get("ui.show_hidden_files", False)
            show_hidden_action.setChecked(show_hidden)
            show_hidden_action.triggered.connect(self._on_toggle_hidden_files)
            menu.addAction(show_hidden_action)
        
        # 显示菜单
        menu.exec_(self.file_view.mapToGlobal(pos))
    
    def _get_main_window(self):
        """
        获取主窗口实例
        
        Returns:
            MainWindow: 主窗口实例，找不到则返回None
        """
        widget = self.parent()
        while widget:
            if widget.__class__.__name__ == 'MainWindow':
                return widget
            widget = widget.parent()
        return None
    
    def _on_toggle_hidden_files(self, checked: bool):
        """
        切换显示隐藏文件
        
        Args:
            checked: 是否显示隐藏文件
        """
        try:
            # 保存配置
            config_manager.set("ui.show_hidden_files", checked)
            
            # 同步主窗口菜单栏状态
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'show_hidden_action'):
                main_window.show_hidden_action.setChecked(checked)
            
            # 刷新文件列表
            dual_pane = self.parent()
            if dual_pane and hasattr(dual_pane, 'set_show_hidden_files'):
                dual_pane.set_show_hidden_files(checked)
            
            logger.info(f"右键菜单切换显示隐藏文件: {checked}")
        
        except Exception as e:
            logger.error(f"切换显示隐藏文件失败: {e}")
    
    def update_file_list_font(self):
        """
        更新文件列表的字体和字号
        """
        from PySide6.QtGui import QFont
        
        # 从配置文件获取字体设置
        folder_font = config_manager.get("ui.folder_font", "Microsoft YaHei")
        folder_font_size = config_manager.get("ui.folder_font_size", 10)
        file_font = config_manager.get("ui.file_font", "Microsoft YaHei")
        file_font_size = config_manager.get("ui.file_font_size", 10)
        
        # 设置文件列表的字体
        # 对于QTreeView，我们设置整个视图的字体
        # 注意：如果需要区分文件夹和文件的字体，需要使用自定义委托
        font = QFont(folder_font, folder_font_size)
        self.file_view.setFont(font)
        
        # 对于QTreeView，还需要更新标题栏字体
        if isinstance(self.file_view, QTreeView):
            header_font = QFont(folder_font, folder_font_size)
            self.file_view.header().setFont(header_font)
        
        logger.info(f"{self.pane_type}窗格已更新文件列表字体")
        
    def update_drive_button_style(self, has_focus):
        """
        更新磁盘选择按钮的样式，区分焦点窗口
        
        Args:
            has_focus: 是否有焦点
        """
        if has_focus:
            # 有焦点时的样式 - 蓝色边框
            style = """
                QPushButton {
                    background-color: #E5F1FB;
                    border: 2px solid #0078D4;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: "Segoe UI";
                    font-size: 9pt;
                    color: #000000;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #CCE4F7;
                    border: 2px solid #0078D4;
                }
            """
        else:
            # 无焦点时的样式 - 灰色边框
            style = """
                QPushButton {
                    background-color: #F5F5F5;
                    border: 1px solid #E5E5E5;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: "Segoe UI";
                    font-size: 9pt;
                    color: #000000;
                }
                QPushButton:hover {
                    background-color: #E5E5E5;
                    border: 1px solid #D5D5D5;
                }
            """
        
        if hasattr(self, 'disk_selector') and self.disk_selector:
            self.disk_selector._button.setStyleSheet(style)
    
    def apply_theme(self, theme_name: str):
        """
        应用主题
        
        Args:
            theme_name: 主题名称（"light"或"dark"）
        """
        if hasattr(self, 'win11_address_bar'):
            self.win11_address_bar.apply_theme(theme_name)
    
    def _on_focus_in(self, event):
        """
        处理焦点进入事件
        
        Args:
            event: 焦点事件对象
        """
        logger.info(f"=== {self.pane_type}窗格_on_focus_in被调用 ===")
        
        # 调用父类的焦点事件处理
        if hasattr(event, 'accept'):
            event.accept()
        
        logger.info(f"{self.pane_type}窗格获得焦点，更新样式")
        
        # 更新磁盘按钮样式
        self.update_drive_button_style(True)
        
        # 更新地址栏样式
        self._update_address_bar_style(True)
        
        # 获取父组件DualPane实例
        dual_pane = self.get_dual_pane_parent()
        if dual_pane:
            # 更新最后有焦点的窗格
            dual_pane.last_focused_pane = self.pane_type
            
            # 更新另一个窗格的样式（失去焦点）
            other_pane = dual_pane.right_pane if self.pane_type == "left" else dual_pane.left_pane
            if other_pane:
                logger.info(f"更新{other_pane.pane_type}窗格失去焦点样式")
                other_pane.update_drive_button_style(False)
                other_pane._update_address_bar_style(False)
            
            # 获取主窗口实例
            main_window = dual_pane.parent()
            while main_window and not hasattr(main_window, 'main_toolbar'):
                main_window = main_window.parent()
            
            # 更新主窗口的工具栏状态
            if main_window:
                # 设置视图模式下拉框
                mode_map = {
                    "icon": 0,
                    "list": 1,
                    "detail": 2,
                    "thumbnail": 3,
                    "tile": 4
                }
                if self.view_mode in mode_map:
                    main_window.view_mode_combo.setCurrentIndex(mode_map[self.view_mode])
                
                # 设置分组模式下拉框
                group_map = {
                    "none": 0,
                    "type": 1,
                    "date": 2,
                    "size": 3
                }
                if self.group_mode in group_map:
                    main_window.group_combo.setCurrentIndex(group_map[self.group_mode])
                
                # 更新菜单选中状态
                main_window.update_menu_check_states()
        
        logger.info(f"{self.pane_type}窗格获得焦点")
    
    def _on_focus_out(self, event):
        """
        处理焦点离开事件
        
        Args:
            event: 焦点事件对象
        """
        # 调用父类的焦点事件处理
        if hasattr(event, 'accept'):
            event.accept()
        
        logger.info(f"{self.pane_type}窗格失去焦点")
    
    def _update_address_bar_style(self, has_focus):
        """
        更新地址栏样式（改为文件列表边框样式）
        
        Args:
            has_focus: 是否有焦点
        """
        # 地址栏样式保持不变
        if hasattr(self, 'win11_address_bar'):
            self.win11_address_bar.set_focus_style(has_focus)
        
        # 只更新文件列表视图的边框样式，不影响标题栏和滚动条
        if has_focus:
            if hasattr(self, 'file_view'):
                self.file_view.setStyleSheet("""
                    QTreeView, QListView {
                        border: 2px solid #0078D4;
                        border-radius: 4px;
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
                    QScrollBar:vertical {
                        width: 4px;
                        background: transparent;
                    }
                    QScrollBar::handle:vertical {
                        background: #C0C0C0;
                        border-radius: 2px;
                        min-height: 20px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #A0A0A0;
                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        width: 0px;
                        height: 0px;
                    }
                """)
        else:
            if hasattr(self, 'file_view'):
                self.file_view.setStyleSheet("""
                    QTreeView, QListView {
                        border: 1px solid #E5E5E5;
                        border-radius: 4px;
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
                    QScrollBar:vertical {
                        width: 4px;
                        background: transparent;
                    }
                    QScrollBar::handle:vertical {
                        background: #C0C0C0;
                        border-radius: 2px;
                        min-height: 20px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #A0A0A0;
                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        width: 0px;
                        height: 0px;
                    }
                """)
    
    def _on_selection_changed(self, selected, deselected):
        """
        选择变化时的处理
        
        Args:
            selected: 选中的索引
            deselected: 取消选中的索引
        """
        dual_pane = self.get_dual_pane_parent()
        if dual_pane:
            dual_pane.update_status_bar()
    
    _MAX_WALK_FILES = 10000

    def get_selected_items_info(self, callback=None):
        """
        获取选中项的详细信息
        
        Args:
            callback: 可选回调函数，后台计算完成后调用(用于更新状态栏)
        
        Returns:
            包含选中项数量、大小、类型等信息的字典
            如果包含文件夹且指定了callback，则先返回快速估算结果，
            后台计算完成后通过Signal通知
        """
        selected_items = self.get_selected_items()
        if not selected_items:
            return {
                "count": 0,
                "file_count": 0,
                "folder_count": 0,
                "subfolder_count": 0,
                "total_size": 0,
                "is_disk": False,
                "disk_info": None
            }
        
        file_count = 0
        folder_count = 0
        subfolder_count = 0
        total_size = 0
        is_disk = False
        disk_info = None
        has_folder_to_walk = False
        
        for item in selected_items:
            file_path = item["path"]
            if os.path.isfile(file_path):
                file_count += 1
                total_size += os.path.getsize(file_path)
            elif os.path.isdir(file_path):
                folder_count += 1
                normalized_path = os.path.normpath(file_path).upper()
                current_is_disk = len(normalized_path) in [2, 3] and normalized_path[1] == ":"
                
                if current_is_disk:
                    is_disk = True
                    try:
                        import ctypes
                        
                        disk_total = ctypes.c_ulonglong(0)
                        disk_free = ctypes.c_ulonglong(0)
                        
                        disk_path = f"{normalized_path[0]}:\\"
                        
                        if ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(disk_path), None, ctypes.byref(disk_total), ctypes.byref(disk_free)):
                            disk_total = disk_total.value
                            disk_free = disk_free.value
                            disk_used = disk_total - disk_free
                            disk_info = {
                                "total": disk_total,
                                "used": disk_used,
                                "free": disk_free
                            }
                        else:
                            disk_info = None
                    except Exception as e:
                        logger.error(f"获取磁盘信息失败: {e}")
                        disk_info = None
                else:
                    has_folder_to_walk = True
        
        if is_disk:
            file_count = 0
            folder_count = 0
            subfolder_count = 0
            total_size = 0
        
        result = {
            "count": len(selected_items),
            "file_count": file_count,
            "folder_count": folder_count,
            "subfolder_count": subfolder_count,
            "total_size": total_size,
            "is_disk": is_disk,
            "disk_info": disk_info
        }

        if has_folder_to_walk and callback is not None:
            self._compute_folder_info_async(selected_items, result, callback)
        
        return result

    def _compute_folder_info_async(self, selected_items, quick_result, callback):
        """在后台线程中计算文件夹详细信息，完成后通过Signal通知UI"""

        def _worker():
            file_count = quick_result["file_count"]
            subfolder_count = quick_result["subfolder_count"]
            total_size = quick_result["total_size"]
            walked_files = 0

            for item in selected_items:
                file_path = item["path"]
                if not os.path.isdir(file_path):
                    continue
                normalized_path = os.path.normpath(file_path).upper()
                if len(normalized_path) in [2, 3] and normalized_path[1] == ":":
                    continue
                try:
                    for root, dirs, files in os.walk(file_path):
                        for f in files:
                            if walked_files >= self._MAX_WALK_FILES:
                                break
                            try:
                                total_size += os.path.getsize(os.path.join(root, f))
                            except (FileNotFoundError, PermissionError, OSError):
                                pass
                            file_count += 1
                            walked_files += 1
                        subfolder_count += len(dirs)
                        if walked_files >= self._MAX_WALK_FILES:
                            break
                except Exception as e:
                    logger.debug(f"操作跳过: {e}")
                    continue
            final_result = dict(quick_result)
            final_result["file_count"] = file_count
            final_result["subfolder_count"] = subfolder_count
            final_result["total_size"] = total_size
            final_result["truncated"] = walked_files >= self._MAX_WALK_FILES

            self.items_info_ready.emit(final_result)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
    
    def cut_selected_items(self):
        """
        剪切选中的文件/文件夹到共享剪贴板
        """
        selected_items = self.get_selected_items()
        dual_pane = self.get_dual_pane_parent()
        if selected_items and dual_pane:
            dual_pane.clipboard_data = {
                "action": "cut",
                "items": selected_items
            }
            logger.info(f"已剪切 {len(selected_items)} 个项目")
    
    def copy_selected_items(self):
        """
        复制选中的文件/文件夹到共享剪贴板
        """
        selected_items = self.get_selected_items()
        dual_pane = self.get_dual_pane_parent()
        if selected_items and dual_pane:
            dual_pane.clipboard_data = {
                "action": "copy",
                "items": selected_items
            }
            logger.info(f"已复制 {len(selected_items)} 个项目")
    
    def get_dual_pane_parent(self):
        """
        获取父组件DualPane实例，通过父组件链查找
        
        Returns:
            DualPane实例或None
        """
        parent = self.parent()
        while parent:
            if hasattr(parent, 'clipboard_data'):
                return parent
            parent = parent.parent()
        return None
    
    def paste_items(self):
        """
        从共享剪贴板粘贴文件/文件夹到当前目录
        """
        import shutil
        
        # 从DualPane获取共享剪贴板数据
        clipboard_data = {"action": None, "items": []}
        dual_pane = self.get_dual_pane_parent()
        if dual_pane:
            clipboard_data = dual_pane.clipboard_data
        
        if not clipboard_data["action"] or not clipboard_data["items"]:
            logger.warning("剪贴板为空")
            return
        
        action = clipboard_data["action"]
        items = clipboard_data["items"]
        
        try:
            for item in items:
                source_path = item["path"]
                file_name = item["name"]
                
                # 对于复制操作，生成唯一路径
                if action == "copy":
                    dest_path = get_unique_path(self.current_path, file_name)
                else:  # 剪切操作，使用原始名称
                    dest_path = os.path.join(self.current_path, file_name)
                
                if action == "copy":
                    if item["is_dir"]:
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
                    logger.info(f"已复制: {source_path} -> {dest_path}")
                elif action == "cut":
                    shutil.move(source_path, dest_path)
                    logger.info(f"已移动: {source_path} -> {dest_path}")
            
            # 刷新当前目录
            self.refresh()
            
            # 如果是剪切操作，清空共享剪贴板
            if action == "cut" and dual_pane:
                dual_pane.clipboard_data = {
                    "action": None,
                    "items": []
                }
        except Exception as e:
            logger.error(f"粘贴失败: {e}")
    
    def delete_selected_items(self):
        """
        删除选中的文件/文件夹
        """
        
        selected_items = self.get_selected_items()
        if not selected_items:
            return
        
        # 显示确认对话框
        count = len(selected_items)
        if count == 1:
            item = selected_items[0]
            message = f"确定要删除 {item['name']} 吗？"
        else:
            message = f"确定要删除选中的 {count} 个项目吗？"
        
        reply = show_question(
            self,
            "确认删除",
            message,
            buttons="yesno"
        )
        
        if reply:
            try:
                import shutil
                for item in selected_items:
                    path = item["path"]
                    if item["is_dir"]:
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    logger.info(f"已删除: {path}")
                
                # 刷新当前目录
                self.refresh()
            except Exception as e:
                logger.error(f"删除失败: {e}")
                show_warning(self, "删除失败", f"删除失败: {e}")
    
    def _on_rename_clicked(self):
        """
        处理重命名点击事件
        """
        from PySide6.QtWidgets import QInputDialog
        
        selected_items = self.get_selected_items()
        if not selected_items or len(selected_items) != 1:
            return
        
        item = selected_items[0]
        old_name = item["name"]
        old_path = item["path"]
        
        # 显示重命名对话框
        new_name, ok = QInputDialog.getText(
            self,
            "重命名",
            f"请输入新名称:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            try:
                # 构建新路径
                parent_dir = os.path.dirname(old_path)
                new_path = os.path.join(parent_dir, new_name)
                
                if os.path.exists(new_path):
                    logger.warning(f"文件已存在: {new_path}")
                    return
                
                # 执行重命名
                os.rename(old_path, new_path)
                logger.info(f"已重命名: {old_path} -> {new_path}")
                
                # 刷新当前目录
                self.refresh()
            except Exception as e:
                logger.error(f"重命名失败: {e}")
    
    def create_new_folder(self):
        """
        创建新文件夹
        """
        from PySide6.QtWidgets import QInputDialog
        
        # 显示新建文件夹对话框
        folder_name, ok = QInputDialog.getText(
            self,
            "新建文件夹",
            "请输入文件夹名称:",
            text="新建文件夹"
        )
        
        if ok and folder_name:
            try:
                # 构建新文件夹路径
                folder_path = os.path.join(self.current_path, folder_name)
                
                if os.path.exists(folder_path):
                    logger.warning(f"文件夹已存在: {folder_path}")
                    return
                
                # 创建文件夹
                os.makedirs(folder_path)
                logger.info(f"已创建文件夹: {folder_path}")
                
                # 刷新当前目录
                self.refresh()
            except Exception as e:
                logger.error(f"创建文件夹失败: {e}")
    
    def create_new_file(self):
        """
        创建新文件
        """
        from PySide6.QtWidgets import QInputDialog
        
        # 显示新建文件对话框
        file_name, ok = QInputDialog.getText(
            self,
            "新建文件",
            "请输入文件名称:",
            text="新建文件.txt"
        )
        
        if ok and file_name:
            try:
                # 构建新文件路径
                file_path = os.path.join(self.current_path, file_name)
                
                if os.path.exists(file_path):
                    logger.warning(f"文件已存在: {file_path}")
                    return
                
                # 创建文件
                with open(file_path, 'w') as f:
                    pass
                logger.info(f"已创建文件: {file_path}")
                
                # 刷新当前目录
                self.refresh()
            except Exception as e:
                logger.error(f"创建文件失败: {e}")
    
    def _on_properties_clicked(self):
        """
        显示文件/文件夹属性
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
        
        selected_items = self.get_selected_items()
        if not selected_items or len(selected_items) != 1:
            return
        
        item = selected_items[0]
        file_path = item["path"]
        is_dir = item["is_dir"]
        
        # 获取文件属性
        stat_info = os.stat(file_path)
        
        # 创建属性对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{item['name']} 属性")
        dialog.setMinimumWidth(400)
        
        # 创建布局
        main_layout = QVBoxLayout(dialog)
        
        # 创建信息容器
        info_layout = QVBoxLayout()
        main_layout.addLayout(info_layout)
        
        # 添加基本信息
        info_layout.addWidget(QLabel(f"名称: {item['name']}"))
        info_layout.addWidget(QLabel(f"类型: {'文件夹' if is_dir else '文件'}"))
        info_layout.addWidget(QLabel(f"位置: {os.path.dirname(file_path)}"))
        
        # 检查是否为磁盘
        normalized_path = os.path.normpath(file_path).upper()
        is_disk = len(normalized_path) in [2, 3] and normalized_path[1] == ":"
        
        if is_disk:
            # 对于磁盘，显示磁盘详细信息
            try:
                import ctypes
                
                disk_total = ctypes.c_ulonglong(0)
                disk_free = ctypes.c_ulonglong(0)
                
                # 确保路径格式为 X:\
                disk_path = f"{normalized_path[0]}:\\"
                
                # 获取磁盘总大小和可用空间
                if ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(disk_path), None, ctypes.byref(disk_total), ctypes.byref(disk_free)):
                    disk_total = disk_total.value
                    disk_free = disk_free.value
                    disk_used = disk_total - disk_free
                    
                    # 转换为GB并保留两位小数
                    total_gb = disk_total / (1024**3)
                    used_gb = disk_used / (1024**3)
                    free_gb = disk_free / (1024**3)
                    
                    # 显示磁盘信息 - 只显示空间信息，不显示文件夹和文件数量以提高性能
                    info_layout.addWidget(QLabel(f"总大小: {total_gb:.2f} GB"))
                    info_layout.addWidget(QLabel(f"已用空间: {used_gb:.2f} GB"))
                    info_layout.addWidget(QLabel(f"可用空间: {free_gb:.2f} GB"))
                else:
                    info_layout.addWidget(QLabel("无法获取磁盘信息"))
            except Exception as e:
                logger.error(f"获取磁盘属性失败: {e}")
                info_layout.addWidget(QLabel(f"获取磁盘信息失败: {e}"))
        elif is_dir:
            # 对于文件夹，计算大小
            folder_size = get_folder_size(file_path)
            info_layout.addWidget(QLabel(f"大小: {folder_size} 字节"))
            
            # 计算文件夹数和文件数 - 使用更高效的方式
            folder_count = 0
            file_count = 0
            try:
                # 使用os.scandir代替os.walk，只扫描当前目录
                with os.scandir(file_path) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                folder_count += 1
                            elif entry.is_file(follow_symlinks=False):
                                file_count += 1
                        except (FileNotFoundError, PermissionError, OSError):
                            # 跳过无法访问的条目
                            continue
            except (FileNotFoundError, PermissionError, OSError):
                # 跳过无法访问的目录
                pass
            
            info_layout.addWidget(QLabel(f"下辖文件夹数: {folder_count}"))
            info_layout.addWidget(QLabel(f"文件数: {file_count}"))
        else:
            # 对于文件，显示文件大小
            info_layout.addWidget(QLabel(f"大小: {stat_info.st_size} 字节"))
        
        # 显示创建时间、修改时间和访问时间
        info_layout.addWidget(QLabel(f"创建时间: {format_time(stat_info.st_ctime)}"))
        info_layout.addWidget(QLabel(f"修改时间: {format_time(stat_info.st_mtime)}"))
        info_layout.addWidget(QLabel(f"访问时间: {format_time(stat_info.st_atime)}"))
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        main_layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec()
    
    def _preview_file(self, file_path):
        """
        预览文件
        
        Args:
            file_path: 文件路径
        """
        import os
        if os.path.isfile(file_path):
            dual_pane = self.get_dual_pane_parent()
            if dual_pane and hasattr(dual_pane, 'function_panel'):
                dual_pane.function_panel.update_preview(file_path)
    
    def _preview_in_new_window(self, file_path):
        """
        在新窗口中预览文件
        
        Args:
            file_path: 文件路径
        """
        import os
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        from services.preview_service import preview_service
        
        if os.path.isfile(file_path):
            # 创建新的弹出窗口
            dialog = QDialog(self)
            dialog.setWindowTitle(f"预览: {os.path.basename(file_path)}")
            dialog.setMinimumSize(800, 600)
            
            # 创建布局
            layout = QVBoxLayout(dialog)
            
            # 生成预览内容
            preview_widget = preview_service.preview_file(file_path, dialog)
            
            # 添加到布局
            layout.addWidget(preview_widget)
            
            # 显示窗口
            dialog.exec()
    
    def _verify_file(self, file_path):
        """
        将文件添加到文件校验的文件输入框内
        
        Args:
            file_path: 文件路径
        """
        import os
        if os.path.isfile(file_path):
            dual_pane = self.get_dual_pane_parent()
            if dual_pane and hasattr(dual_pane, 'function_panel'):
                # 确保功能面板可见
                if not dual_pane.function_panel.isVisible():
                    dual_pane.function_panel.setVisible(True)
                
                # 将文件添加到文件校验的文件输入框内
                if hasattr(dual_pane.function_panel, 'add_files_to_verify'):
                    dual_pane.function_panel.add_files_to_verify([file_path])
    
    def _add_to_compare(self, file_path, target):
        """
        将文件添加到对比
        
        Args:
            file_path: 文件路径
            target: 目标位置，1表示文件一，2表示文件二
        """
        import os
        if os.path.exists(file_path):
            dual_pane = self.get_dual_pane_parent()
            if dual_pane and hasattr(dual_pane, 'function_panel'):
                # 确保功能面板可见
                if not dual_pane.function_panel.isVisible():
                    dual_pane.function_panel.setVisible(True)
                
                # 切换到对比标签
                dual_pane.function_panel.switch_to_tab("对比")
                
                # 将文件添加到对应输入框
                if target == 1:
                    dual_pane.function_panel.file1_edit.setText(file_path)
                else:
                    dual_pane.function_panel.file2_edit.setText(file_path)
    
    def _copy_file_name(self, file_path):
        """
        复制文件名到剪贴板
        
        Args:
            file_path: 文件路径
        """
        from PySide6.QtWidgets import QApplication
        
        try:
            file_name = os.path.basename(file_path)
            clipboard = QApplication.clipboard()
            clipboard.setText(file_name)
            logger.info(f"已复制文件名: {file_name}")
        except Exception as e:
            logger.error(f"复制文件名失败: {e}")
    
    def _copy_file_path(self, file_path):
        """
        复制文件路径到剪贴板
        
        Args:
            file_path: 文件路径
        """
        from PySide6.QtWidgets import QApplication
        
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)
            logger.info(f"已复制文件路径: {file_path}")
        except Exception as e:
            logger.error(f"复制文件路径失败: {e}")
    
    def _adjust_column_widths(self):
        """
        调整列宽以适应内容
        """
        if isinstance(self.file_view, QTreeView):
            for column in range(self.model.columnCount()):
                self.file_view.resizeColumnToContents(column)
    
    def _open_parent_folder(self, file_path):
        """
        打开文件所在的文件夹
        
        Args:
            file_path: 文件路径
        """
        import os
        import subprocess
        
        try:
            # 获取父文件夹路径
            parent_folder = os.path.dirname(file_path)
            
            # 打开父文件夹
            if os.name == 'nt':  # Windows
                os.startfile(parent_folder)
            elif os.name == 'posix':  # Linux/macOS
                subprocess.call(['open', parent_folder])
            
            logger.info(f"已打开文件夹: {parent_folder}")
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}")
    
    def _drag_enter_event(self, event):
        """
        处理拖放进入事件
        
        Args:
            event: 拖放事件对象
        """
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
    
    def _drag_move_event(self, event):
        """
        处理拖放移动事件
        
        Args:
            event: 拖放事件对象
        """
        event.acceptProposedAction()
    
    def _drop_event(self, event):
        """
        处理拖放释放事件
        
        Args:
            event: 拖放事件对象
        """
        from PySide6.QtWidgets import QMenu
        
        # 获取目标位置
        target_index = self.file_view.indexAt(event.position().toPoint())
        
        # 获取目标路径
        if target_index.isValid():
            # 转换为源模型索引
            source_index = self.proxy_model.mapToSource(target_index)
            target_path = self.model.filePath(source_index)
            # 如果目标是文件，使用其所在目录
            if not self.model.isDir(source_index):
                target_path = os.path.dirname(target_path)
        else:
            # 拖放到空白处，使用当前目录
            target_path = self.current_path
        
        # 检查拖放数据
        if event.mimeData().hasUrls():
            # 从外部应用拖入
            urls = event.mimeData().urls()
            source_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        elif event.mimeData().hasText():
            # 从内部拖入
            source_paths = event.mimeData().text().split('\n')
        else:
            event.ignore()
            return
        
        # 过滤空路径
        source_paths = [path for path in source_paths if path]
        if not source_paths:
            event.ignore()
            return
        
        # 显示拖放操作菜单
        menu = QMenu(self)
        copy_action = menu.addAction("复制到此处")
        move_action = menu.addAction("移动到此处")
        
        # 计算菜单位置
        menu_pos = self.file_view.mapToGlobal(event.position().toPoint())
        
        # 执行用户选择的操作
        selected_action = menu.exec(menu_pos)
        if selected_action == copy_action:
            # 执行复制操作
            self._copy_files(source_paths, target_path)
            event.setDropAction(Qt.CopyAction)
        elif selected_action == move_action:
            # 执行移动操作
            self._move_files(source_paths, target_path)
            event.setDropAction(Qt.MoveAction)
        else:
            # 用户取消操作
            event.ignore()
            return
        
        event.accept()
    
    def _copy_files(self, source_paths, target_path):
        """
        复制文件/文件夹到目标路径
        
        Args:
            source_paths: 源文件/文件夹路径列表
            target_path: 目标路径
        """
        import shutil
        
        try:
            for source_path in source_paths:
                if os.path.isdir(source_path):
                    # 复制文件夹
                    dest_folder_name = os.path.basename(source_path)
                    dest_path = get_unique_path(target_path, dest_folder_name)
                    shutil.copytree(source_path, dest_path)
                    logger.info(f"已复制文件夹: {source_path} -> {dest_path}")
                else:
                    # 复制文件
                    file_name = os.path.basename(source_path)
                    dest_path = get_unique_path(target_path, file_name)
                    shutil.copy2(source_path, dest_path)
                    logger.info(f"已复制文件: {source_path} -> {dest_path}")
            
            # 刷新当前目录
            self.refresh()
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            show_warning(self, "复制失败", f"复制文件失败: {e}")
    
    def _move_files(self, source_paths, target_path):
        """
        移动文件/文件夹到目标路径
        
        Args:
            source_paths: 源文件/文件夹路径列表
            target_path: 目标路径
        """
        import shutil
        
        try:
            for source_path in source_paths:
                # 检查源文件和目标是否在同一驱动器
                source_drive = os.path.splitdrive(source_path)[0]
                target_drive = os.path.splitdrive(target_path)[0]
                
                dest_name = os.path.basename(source_path)
                dest_path = get_unique_path(target_path, dest_name)
                
                shutil.move(source_path, dest_path)
                logger.info(f"已移动: {source_path} -> {dest_path}")
            
            # 刷新当前目录
            self.refresh()
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            show_warning(self, "移动失败", f"移动文件失败: {e}")
    
    def _compress_items(self, source_paths):
        """
        压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
        """
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from services.compression_service import compression_service
        
        # 选择保存位置和文件名
        dest_path, _ = QFileDialog.getSaveFileName(self, "保存压缩文件", ".", "压缩文件 (*.zip *.7z *.tar *.tar.gz *.tar.bz2 *.tar.xz)")
        if not dest_path:
            return
        
        # 选择压缩格式
        formats = compression_service.get_supported_formats()
        format, ok = QInputDialog.getItem(self, "选择压缩格式", "压缩格式:", formats, 0, False)
        if not ok:
            return
        
        # 选择压缩级别
        level, ok = QInputDialog.getInt(self, "选择压缩级别", "压缩级别 (1-9):", 6, 1, 9, 1)
        if not ok:
            return
        
        # 执行压缩
        success = compression_service.compress(source_paths, dest_path, format, level)
        if success:
            show_info(self, "成功", f"压缩成功: {dest_path}")
            self.refresh()
        else:
            show_warning(self, "失败", "压缩失败")
    
    def _decompress_file(self, file_path):
        """
        解压压缩文件
        
        Args:
            file_path: 压缩文件路径
        """
        from PySide6.QtWidgets import QFileDialog
        from services.compression_service import compression_service
        
        # 选择解压位置
        dest_path = QFileDialog.getExistingDirectory(self, "选择解压位置", os.path.dirname(file_path))
        if not dest_path:
            return
        
        # 执行解压
        success = compression_service.decompress(file_path, dest_path)
        if success:
            show_info(self, "成功", f"解压成功: {dest_path}")
            self.refresh()
        else:
            show_warning(self, "失败", "解压失败")
    
    def _get_send_to_targets(self):
        """
        获取Windows发送到菜单的目标列表
        
        Returns:
            发送到目标列表，每个元素为(名称, 路径)元组
        """
        if os.name != 'nt':
            return []
        
        send_to_targets = []
        
        try:
            # 获取发送到目录路径

            appdata = os.environ.get('APPDATA', '')
            send_to_dir = os.path.join(appdata, 'Microsoft', 'Windows', 'SendTo')
            
            if not os.path.exists(send_to_dir):
                return []
            
            # 遍历发送到目录
            for entry in os.listdir(send_to_dir):
                entry_path = os.path.join(send_to_dir, entry)
                
                # 跳过隐藏文件
                if entry.startswith('.'):
                    continue
                
                # 获取名称（去除扩展名）
                name = os.path.splitext(entry)[0]
                
                # 常用发送到目标的中英文对照
                name_mapping = {
                    'Bluetooth': '蓝牙设备',
                    'Desktop': '桌面',
                    'Documents': '文档',
                    'Downloads': '下载',
                    'Mail Recipient': '邮件收件人',
                    'OneDrive': 'OneDrive',
                    'Compressed (zipped) Folder': '压缩(zipped)文件夹',
                    'Fax Recipient': '传真收件人',
                }
                
                # 转換為中文名稱
                display_name = name_mapping.get(name, name)
                
                # 添加到列表
                send_to_targets.append((display_name, entry_path))
            
            # 按名称排序
            send_to_targets.sort(key=lambda x: x[0].lower())
            
        except Exception as e:
            logger.warning(f"获取发送到目标失败: {e}")
        
        return send_to_targets
    
    def _send_to_target(self, file_path, target_path):
        """
        发送文件到指定目标
        
        Args:
            file_path: 要发送的文件路径
            target_path: 目标路径（可以是文件夹、程序快捷方式等）
        """
        try:
            import subprocess
            
            # 检查目标类型
            if os.path.isdir(target_path):
                # 目标是文件夹，复制文件到该文件夹
                import shutil
                dest_path = os.path.join(target_path, os.path.basename(file_path))
                shutil.copy2(file_path, dest_path)
                show_info(self, "成功", f"文件已发送到: {target_path}")
            else:
                # 目标是程序快捷方式或文件，使用系统关联打开
                # 使用ShellExecute打开目标并传递文件作为参数
                if os.name == 'nt':
                    import subprocess
                    subprocess.Popen([target_path, file_path])
                else:
                    subprocess.Popen([target_path, file_path])
            
        except Exception as e:
            logger.error(f"发送到目标失败: {e}")
            show_warning(self, "失败", f"发送失败: {str(e)}")
    
    def _start_drag(self, supported_actions):
        """
        处理拖放开始事件
        
        Args:
            supported_actions: 支持的拖放操作
        """
        from PySide6.QtGui import QDrag
        from PySide6.QtCore import QMimeData
        
        # 获取选中的文件/文件夹
        selected_items = self.get_selected_items()
        if not selected_items:
            return
        
        # 创建拖放数据
        mime_data = QMimeData()
        
        # 添加文件路径列表
        file_paths = [item["path"] for item in selected_items]
        mime_data.setText("\n".join(file_paths))
        
        # 添加URL列表（用于外部应用拖放）
        urls = [QUrl.fromLocalFile(path) for path in file_paths]
        mime_data.setUrls(urls)
        
        # 创建拖放对象
        drag = QDrag(self.file_view)
        drag.setMimeData(mime_data)
        
        # 执行拖放
        drag.exec(supported_actions)
    
    def set_view_mode(self, view_mode):
        """
        设置视图模式
        
        Args:
            view_mode: 视图模式，"detail"、"icon"、"list"、"thumbnail"或"tile"
        """
        if view_mode != self.view_mode:
            # 保存当前路径
            current_path = self.get_current_path()
            
            # 保存焦点状态
            had_focus = False
            dual_pane = self.get_dual_pane_parent()
            if dual_pane and dual_pane.last_focused_pane == self.pane_type:
                had_focus = True
            
            # 保存旧视图引用
            old_view = self.file_view
            
            # 创建新视图
            if view_mode == "detail":
                self.file_view = QTreeView()
                self.file_view.setRootIsDecorated(False)
                self.file_view.setItemsExpandable(False)
                self.file_view.setAlternatingRowColors(True)
                self.file_view.setAllColumnsShowFocus(True)
                self.file_view.setSortingEnabled(True)
                self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                # 设置默认按名称升序排序
                self.file_view.sortByColumn(0, Qt.AscendingOrder)
                # 延迟调整列宽，确保模型已加载数据且窗格已完全显示
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, lambda: self._adjust_column_widths())
                # 重新连接信号
                self.file_view.doubleClicked.connect(self._on_double_click)
                self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
                self.file_view.customContextMenuRequested.connect(self._show_context_menu)
                # 重新连接焦点事件
                self.file_view.focusInEvent = self._on_focus_in
                self.file_view.focusOutEvent = self._on_focus_out

            else:
                self.file_view = QListView()
                
                # 根据不同的视图模式设置不同的属性
                if view_mode == "list":
                    self.file_view.setViewMode(QListView.ListMode)
                    self.file_view.setIconSize(QSize(24, 24))
                    self.file_view.setUniformItemSizes(True)
                    self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                elif view_mode == "thumbnail":
                    self.file_view.setViewMode(QListView.IconMode)
                    self.file_view.setIconSize(QSize(128, 128))
                    self.file_view.setUniformItemSizes(True)
                    self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                    self.file_view.setSpacing(10)
                elif view_mode == "tile":
                    self.file_view.setViewMode(QListView.IconMode)
                    self.file_view.setIconSize(QSize(96, 96))
                    self.file_view.setUniformItemSizes(True)
                    self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                    self.file_view.setSpacing(8)
                else:  # icon模式
                    self.file_view.setViewMode(QListView.IconMode)
                    self.file_view.setIconSize(QSize(64, 64))
                    self.file_view.setUniformItemSizes(True)
                    self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                    self.file_view.setSpacing(8)
                
                # 重新连接信号
                self.file_view.doubleClicked.connect(self._on_double_click)
                self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
                self.file_view.customContextMenuRequested.connect(self._show_context_menu)
                # 重新连接焦点事件
                self.file_view.focusInEvent = self._on_focus_in
                self.file_view.focusOutEvent = self._on_focus_out
            
            # 使用代理模型来显示中文标题
            self.file_view.setModel(self.proxy_model)
            
            # 连接选择变化事件（必须在设置模型之后）
            self.file_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
            
            # 立即设置根索引，避免显示根路径下的所有磁盘
            if current_path:
                # 设置模型的根路径
                root_index = self.model.setRootPath(current_path)
                # 将源模型的索引转换为代理模型的索引
                proxy_index = self.proxy_model.mapFromSource(root_index)
                # 设置视图的根索引
                self.file_view.setRootIndex(proxy_index)
            
            # 添加新视图到布局中
            layout = self.layout()
            if layout is not None:
                # 移除旧视图，保留导航栏
                layout.removeWidget(old_view)
                # 添加新视图
                layout.addWidget(self.file_view)
            
            # 更新字体设置
            self.update_file_list_font()
            
            # 恢复路径（更新地址栏和历史记录）
            self.set_current_path(current_path)
            
            # 更新当前视图模式
            self.view_mode = view_mode
            
            # 恢复焦点状态
            if had_focus:
                # 延迟恢复焦点，确保新视图已经完全加载
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._on_focus_in(None))
            
            logger.info(f"{self.pane_type}窗格视图模式已切换为: {view_mode}")
    
    def set_group_mode(self, mode):
        """
        设置分组模式
        
        Args:
            mode: 分组模式
        """
        if mode != self.group_mode:
            # 保存当前路径
            current_path = self.get_current_path()
            
            # 保存焦点状态
            had_focus = False
            dual_pane = self.get_dual_pane_parent()
            if dual_pane and dual_pane.last_focused_pane == self.pane_type:
                had_focus = True
            
            # 记录分组模式
            logger.info(f"{self.pane_type}窗格分组模式已设置为: {mode}")
            
            # 更新分组模式
            self.group_mode = mode
            
            # 根据分组模式设置视图
            if mode != "none":
                # 使用分组视图
                from ui.file_list_view.grouped_file_list_view import GroupedFileListView
                
                # 保存旧视图引用
                old_view = self.file_view
                
                # 创建分组视图
                self.file_view = GroupedFileListView()
                self.file_view.set_group_mode(mode)
                self.file_view.item_activated.connect(self._on_double_click_grouped)
                self.file_view.item_context_menu.connect(self._show_context_menu_grouped)
                self.file_view.selection_changed.connect(self._on_selection_changed_grouped)
                self.file_view.focusInEvent = self._on_focus_in
                self.file_view.focusOutEvent = self._on_focus_out
                
                # 设置当前路径
                if current_path:
                    self.file_view.set_path(current_path)
                
                # 添加新视图到布局中
                layout = self.layout()
                if layout is not None:
                    # 移除旧视图，保留导航栏
                    layout.removeWidget(old_view)
                    # 添加新视图
                    layout.addWidget(self.file_view)
                
                # 更新字体设置
                self.update_file_list_font()
            else:
                # 恢复为普通视图
                if isinstance(self.file_view, QTreeView):
                    # 对于详细视图，我们启用排序作为分组的替代方案
                    self.file_view.setSortingEnabled(True)
                    self.file_view.sortByColumn(0, Qt.AscendingOrder)  # 名称列
                elif isinstance(self.file_view, QListView):
                    # 对于QListView，我们通过模型排序来实现分组效果
                    # QFileSystemModel支持排序，我们可以直接调用其sort方法
                    self.model.sort(0, Qt.AscendingOrder)
                else:
                    # 如果是分组视图，切换回普通视图
                    old_view = self.file_view
                    
                    # 根据当前视图模式创建普通视图
                    if self.view_mode == "detail":
                        self.file_view = QTreeView()
                        self.file_view.setRootIsDecorated(False)
                        self.file_view.setItemsExpandable(False)
                        self.file_view.setAlternatingRowColors(True)
                        self.file_view.setAllColumnsShowFocus(True)
                        self.file_view.setSortingEnabled(True)
                        self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                        self.file_view.sortByColumn(0, Qt.AscendingOrder)
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(100, lambda: self._adjust_column_widths())
                    else:
                        self.file_view = QListView()
                        if self.view_mode == "list":
                            self.file_view.setViewMode(QListView.ListMode)
                            self.file_view.setIconSize(QSize(24, 24))
                        elif self.view_mode == "thumbnail":
                            self.file_view.setViewMode(QListView.IconMode)
                            self.file_view.setIconSize(QSize(128, 128))
                            self.file_view.setSpacing(10)
                        elif self.view_mode == "tile":
                            self.file_view.setViewMode(QListView.IconMode)
                            self.file_view.setIconSize(QSize(96, 96))
                            self.file_view.setSpacing(8)
                        else:
                            self.file_view.setViewMode(QListView.IconMode)
                            self.file_view.setIconSize(QSize(64, 64))
                            self.file_view.setSpacing(8)
                        self.file_view.setUniformItemSizes(True)
                        self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
                    
                    # 重新连接信号
                    self.file_view.setModel(self.proxy_model)
                    self.file_view.doubleClicked.connect(self._on_double_click)
                    self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.file_view.customContextMenuRequested.connect(self._show_context_menu)
                    self.file_view.focusInEvent = self._on_focus_in
                    self.file_view.focusOutEvent = self._on_focus_out
                    self.file_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
                    
                    # 设置当前路径
                    if current_path:
                        root_index = self.model.setRootPath(current_path)
                        proxy_index = self.proxy_model.mapFromSource(root_index)
                        self.file_view.setRootIndex(proxy_index)
                    
                    # 添加新视图到布局中
                    layout = self.layout()
                    if layout is not None:
                        layout.removeWidget(old_view)
                        layout.addWidget(self.file_view)
                    
                    self.update_file_list_font()
            
            # 恢复焦点状态
            if had_focus:
                # 延迟恢复焦点，确保新视图已经完全加载
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._on_focus_in(None))
    
    def _on_double_click_grouped(self, path):
        """处理分组视图的双击事件"""
        if os.path.isdir(path):
            self.set_current_path(path)
        else:
            # 打开文件
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    
    def _show_context_menu_grouped(self, path, pos):
        """处理分组视图的右键菜单"""
        # 复用现有的右键菜单逻辑
        self._show_context_menu(pos)
    
    def _on_selection_changed_grouped(self, paths):
        """处理分组视图的选择变化"""
        # 更新状态栏
        dual_pane = self.get_dual_pane_parent()
        if dual_pane:
            dual_pane.update_status_bar()

class DualPane(QWidget):
    """
    双窗格组件
    包含左右两个窗格和功能面板
    """

    def __init__(self, parent=None):
        """
        初始化双窗格组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        # 初始化共享剪贴板数据
        self.clipboard_data = {
            "action": None,  # "cut" or "copy"
            "items": []
        }
        # 初始化同步窗格设置
        self.sync_panes = config_manager.get("ui.sync_panes", True)
        # 记录最后有焦点的窗格
        self.last_focused_pane = "left"
        self.init_ui()
    
    def init_ui(self):
        """
        初始化双窗格UI组件
        """
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建分隔器
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # 创建左侧窗格
        self.left_pane = PaneWidget(self, "left")
        self.splitter.addWidget(self.left_pane)
        
        # 创建右侧窗格
        self.right_pane = PaneWidget(self, "right")
        self.splitter.addWidget(self.right_pane)
        
        # 创建功能面板
        self.function_panel = FunctionPanel(self)
        
        # 添加功能面板到分割器
        self.splitter.addWidget(self.function_panel)
        
        # 确保功能面板默认是可见的
        self.function_panel.setVisible(True)
        
        # 连接文件选择信号
        self.function_panel.connect_file_selection(self.left_pane, self.right_pane)
    
    def set_splitter_ratio(self, ratio):
        """
        设置分隔器比例
        
        Args:
            ratio: 分隔器比例列表，如 [0.35, 0.35, 0.3]
        """
        if len(ratio) == self.splitter.count():
            self.splitter.setSizes([int(ratio[i] * self.width()) for i in range(len(ratio))])
    
    def get_splitter_ratio(self):
        """
        获取分隔器比例
        
        Returns:
            分隔器比例列表
        """
        sizes = self.splitter.sizes()
        total = sum(sizes)
        if total == 0:
            return [1.0 / self.splitter.count() for _ in range(self.splitter.count())]
        return [size / total for size in sizes]
    
    def toggle_function_panel(self):
        self.function_panel.setVisible(not self.function_panel.isVisible())
        
        if self.function_panel.isVisible():
            ratio = [4/11, 4/11, 3/11]
            self.set_splitter_ratio(ratio)
        
        self.refresh()
    
    def reset_layout(self):
        self.function_panel.setVisible(True)
        self.set_splitter_ratio([4/11, 4/11, 3/11])
        self.refresh()
    def get_left_pane(self):
        """
        获取左侧窗格
        
        Returns:
            左侧窗格实例
        """
        return self.left_pane
    
    def get_right_pane(self):
        """
        获取右侧窗格
        
        Returns:
            右侧窗格实例
        """
        return self.right_pane
    
    def get_active_pane(self):
        """
        获取当前活动的窗格
        
        Returns:
            当前活动窗格实例（左窗格或右窗格）
        """
        if self.last_focused_pane == "right":
            return self.right_pane
        else:
            return self.left_pane
    
    def switch_function_panel_tab(self, tab_name):
        """
        切换功能面板的标签页
        
        Args:
            tab_name: 标签页名称，可选值："搜索"、"对比"、"预览"、"传输"、"Ftp"、"P2P"、"辅助"
        """
        # 确保功能面板可见
        if not self.function_panel.isVisible():
            self.function_panel.setVisible(True)
            # 重新分布窗格宽度
            total_width = self.splitter.width()
            # 设置合理的分隔比例
            ratio = [4/11, 4/11, 3/11]
            self.set_splitter_ratio(ratio)
        
        # 切换到指定标签页
        self.function_panel.switch_to_tab(tab_name)
    
    def switch_to_tools_tab(self, tool_name):
        """
        切换到辅助标签内的相应子标签
        
        Args:
            tool_name: 工具名称，可选值："批量重命名"、"文件编码转换"、"图片格式转换"、"文件校验"
        """
        # 确保功能面板可见
        if not self.function_panel.isVisible():
            self.function_panel.setVisible(True)
            # 重新分布窗格宽度
            total_width = self.splitter.width()
            # 设置合理的分隔比例
            ratio = [4/11, 4/11, 3/11]
            self.set_splitter_ratio(ratio)
        
        # 切换到辅助标签
        self.function_panel.switch_to_tab("辅助")
        
        # 切换到辅助标签内的相应子标签
        if hasattr(self.function_panel, 'tools_tab_widget'):
            for i in range(self.function_panel.tools_tab_widget.count()):
                if self.function_panel.tools_tab_widget.tabText(i) == tool_name:
                    self.function_panel.tools_tab_widget.setCurrentIndex(i)
                    break
    
    def get_function_panel(self):
        """
        获取功能面板实例
        
        Returns:
            FunctionPanel: 功能面板实例
        """
        return self.function_panel
    
    def _add_to_compare(self, file_path, target):
        """
        将文件添加到对比
        
        Args:
            file_path: 文件路径
            target: 目标位置，1表示文件一，2表示文件二
        """
        # 获取父组件DualPane
        dual_pane = self.parent()
        if not dual_pane:
            return
        
        # 确保功能面板可见
        if hasattr(dual_pane, 'function_panel'):
            if not dual_pane.function_panel.isVisible():
                dual_pane.function_panel.setVisible(True)
            
            # 切换到对比标签
            dual_pane.function_panel.switch_to_tab("对比")
            
            # 将文件添加到对应输入框
            if target == 1:
                dual_pane.function_panel.file1_edit.setText(file_path)
            else:
                dual_pane.function_panel.file2_edit.setText(file_path)
    
    def preview_selected_file(self):
        """
        预览当前选中的文件
        """
        # 检查左侧窗格是否有选中的文件
        left_selected = self.left_pane.get_selected_items()
        right_selected = self.right_pane.get_selected_items()
        
        # 优先使用左侧窗格的选中项，如果没有则使用右侧窗格
        selected_items = left_selected if left_selected else right_selected
        
        # 如果有选中的文件，预览第一个文件
        for item in selected_items:
            if item["type"] == "文件":
                # 先切换到预览标签页
                self.switch_function_panel_tab("预览")
                self.function_panel.update_preview(item["path"])
                return
        
        # 如果没有选中的文件，检查当前激活的窗格
        focused_pane = self.left_pane if self.left_pane.hasFocus() else self.right_pane
        selected_items = focused_pane.get_selected_items()
        for item in selected_items:
            if item["type"] == "文件":
                # 先切换到预览标签页
                self.switch_function_panel_tab("预览")
                self.function_panel.update_preview(item["path"])
                return
    
    def set_show_hidden_files(self, show_hidden):
        """
        设置是否显示隐藏文件
        
        Args:
            show_hidden: 是否显示隐藏文件
        """
        self.left_pane.set_show_hidden_files(show_hidden)
        self.right_pane.set_show_hidden_files(show_hidden)
    
    def apply_theme(self, theme_name: str):
        """
        应用主题到所有窗格
        
        Args:
            theme_name: 主题名称（"light"或"dark"）
        """
        self.left_pane.apply_theme(theme_name)
        self.right_pane.apply_theme(theme_name)
    
    def refresh(self):
        """
        刷新两个窗格的内容
        """
        self.left_pane.refresh()
        self.right_pane.refresh()
    
    @staticmethod
    def _format_pane_info(info, selected_items, label):
        if info["count"] == 0:
            return f"{label}: 未选择文件"
        elif info["is_disk"]:
            if info["disk_info"]:
                free = info["disk_info"]["free"] / (1024**3)
                disk_name = selected_items[0]["name"] if selected_items else ""
                return f"{label}: 磁盘 {disk_name} - 可用: {free:.2f} GB"
            else:
                disk_name = selected_items[0]["name"] if selected_items else ""
                return f"{label}: 磁盘 {disk_name}"
        elif info["count"] == 1:
            if info["file_count"] == 1:
                size_text = format_size(info["total_size"])
                file_path = selected_items[0]["path"]
                file_ext = os.path.splitext(file_path)[1].lower()
                encoding = detect_file_encoding(file_path)
                return f"{label}: 大小: {size_text}, 类型: {file_ext}, 编码: {encoding}"
            else:
                size_text = format_size(info["total_size"])
                suffix = " (计算中...)" if info.get("truncated") else ""
                return f"{label}: 文件夹数: {info['subfolder_count']}, 文件数: {info['file_count']}, 总大小: {size_text}{suffix}"
        else:
            size_text = format_size(info["total_size"])
            suffix = " (计算中...)" if info.get("truncated") else ""
            return f"{label}: 选中 {info['count']} 项 - 文件: {info['file_count']}, 文件夹: {info['folder_count']}, 总大小: {size_text}{suffix}"

    def _on_pane_info_ready(self, pane_side, info):
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parent()
        if not main_window or not hasattr(main_window, 'status_bar'):
            return

        pane = self.left_pane if pane_side == "left" else self.right_pane
        selected_items = pane.get_selected_items()
        label = "左窗" if pane_side == "left" else "右窗"
        text = self._format_pane_info(info, selected_items, label)
        if pane_side == "left":
            main_window.left_pane_info.setText(text)
        else:
            main_window.right_pane_info.setText(text)

    def update_status_bar(self):
        """
        更新主窗口的状态栏信息
        """
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parent()
        
        if not main_window or not hasattr(main_window, 'status_bar'):
            return

        try:
            self.left_pane.items_info_ready.disconnect()
        except RuntimeError:
            pass
        try:
            self.right_pane.items_info_ready.disconnect()
        except RuntimeError:
            pass
        self.left_pane.items_info_ready.connect(lambda info: self._on_pane_info_ready("left", info))
        self.right_pane.items_info_ready.connect(lambda info: self._on_pane_info_ready("right", info))
        
        left_info = self.left_pane.get_selected_items_info(callback=True)
        left_selected_items = self.left_pane.get_selected_items()
        left_text = self._format_pane_info(left_info, left_selected_items, "左窗")
        
        right_info = self.right_pane.get_selected_items_info(callback=True)
        right_selected_items = self.right_pane.get_selected_items()
        right_text = self._format_pane_info(right_info, right_selected_items, "右窗")
        
        main_window.left_pane_info.setText(left_text)
        main_window.right_pane_info.setText(right_text)
    
    def set_view_mode(self, mode, pane=None):
        """
        设置视图模式
        
        Args:
            mode: 视图模式
            pane: 窗格类型，"left"、"right"或None（表示所有窗格）
        """
        if pane == "left":
            self.left_pane.set_view_mode(mode)
            logger.info(f"左侧窗格视图模式已设置为: {mode}")
        elif pane == "right":
            self.right_pane.set_view_mode(mode)
            logger.info(f"右侧窗格视图模式已设置为: {mode}")
        elif pane is None:
            if self.sync_panes:
                # 同步设置所有窗格
                self.left_pane.set_view_mode(mode)
                self.right_pane.set_view_mode(mode)
                logger.info(f"所有窗格视图模式已同步设置为: {mode}")
            else:
                # 不同步时，设置当前焦点窗格或最后有焦点的窗格
                # 检查哪个窗格有焦点
                if self.left_pane.hasFocus() or self.left_pane.file_view.hasFocus():
                    self.left_pane.set_view_mode(mode)
                    logger.info(f"左侧窗格视图模式已设置为: {mode}")
                elif self.right_pane.hasFocus() or self.right_pane.file_view.hasFocus():
                    self.right_pane.set_view_mode(mode)
                    logger.info(f"右侧窗格视图模式已设置为: {mode}")
                else:
                    # 没有焦点时，设置最后有焦点的窗格
                    if self.last_focused_pane == "left":
                        self.left_pane.set_view_mode(mode)
                        logger.info(f"左侧窗格视图模式已设置为: {mode}")
                    else:
                        self.right_pane.set_view_mode(mode)
                        logger.info(f"右侧窗格视图模式已设置为: {mode}")
    
    def set_group_mode(self, mode, pane=None):
        """
        设置分组模式
        
        Args:
            mode: 分组模式
            pane: 窗格类型，"left"、"right"或None（表示所有窗格）
        """
        if pane == "left":
            self.left_pane.set_group_mode(mode)
            logger.info(f"左侧窗格分组模式已设置为: {mode}")
        elif pane == "right":
            self.right_pane.set_group_mode(mode)
            logger.info(f"右侧窗格分组模式已设置为: {mode}")
        elif pane is None:
            if self.sync_panes:
                # 同步设置所有窗格
                self.left_pane.set_group_mode(mode)
                self.right_pane.set_group_mode(mode)
                logger.info(f"所有窗格分组模式已同步设置为: {mode}")
            else:
                # 不同步时，设置当前焦点窗格或最后有焦点的窗格
                # 检查哪个窗格有焦点
                if self.left_pane.hasFocus() or self.left_pane.file_view.hasFocus():
                    self.left_pane.set_group_mode(mode)
                    logger.info(f"左侧窗格分组模式已设置为: {mode}")
                elif self.right_pane.hasFocus() or self.right_pane.file_view.hasFocus():
                    self.right_pane.set_group_mode(mode)
                    logger.info(f"右侧窗格分组模式已设置为: {mode}")
                else:
                    # 没有焦点时，设置最后有焦点的窗格
                    if self.last_focused_pane == "left":
                        self.left_pane.set_group_mode(mode)
                        logger.info(f"左侧窗格分组模式已设置为: {mode}")
                    else:
                        self.right_pane.set_group_mode(mode)
                        logger.info(f"右侧窗格分组模式已设置为: {mode}")
    
    def update_sync_panes_setting(self, sync_panes):
        """
        更新同步窗格设置
        
        Args:
            sync_panes: 是否同步窗格
        """
        self.sync_panes = sync_panes
        logger.info(f"窗格同步设置已更新为: {sync_panes}")
    
    def toggle_right_pane(self):
        """
        切换右侧窗格的显示/隐藏状态
        """
        self.right_pane.setVisible(not self.right_pane.isVisible())
    
    def update_file_list_font(self):
        """
        更新文件列表的字体和字号
        """
        self.left_pane.update_file_list_font()
        self.right_pane.update_file_list_font()
    
    def copy_selected_items(self):
        """
        复制当前焦点窗格中选中的文件或文件夹
        """
        if self.last_focused_pane == "left":
            self.left_pane.copy_selected_items()
        else:
            self.right_pane.copy_selected_items()
    
    def paste_items(self):
        """
        在当前焦点窗格中粘贴文件或文件夹
        """
        if self.last_focused_pane == "left":
            self.left_pane.paste_items()
        else:
            self.right_pane.paste_items()
    
    def delete_selected_items(self):
        """
        删除当前焦点窗格中选中的文件或文件夹
        """
        if self.last_focused_pane == "left":
            self.left_pane.delete_selected_items()
        else:
            self.right_pane.delete_selected_items()
    
    def compress_selected_items(self):
        """
        压缩当前焦点窗格中选中的文件或文件夹
        """
        if self.last_focused_pane == "left":
            selected_items = self.left_pane.get_selected_items()
        else:
            selected_items = self.right_pane.get_selected_items()
        
        if selected_items:
            source_paths = [item["path"] for item in selected_items]
            if self.last_focused_pane == "left":
                self.left_pane._compress_items(source_paths)
            else:
                self.right_pane._compress_items(source_paths)
    
    def decompress_selected_items(self):
        """
        解压当前焦点窗格中选中的压缩文件
        """
        if self.last_focused_pane == "left":
            selected_items = self.left_pane.get_selected_items()
        else:
            selected_items = self.right_pane.get_selected_items()
        
        if len(selected_items) == 1 and not selected_items[0]["is_dir"]:
            file_path = selected_items[0]["path"]
            if self.last_focused_pane == "left":
                self.left_pane._decompress_file(file_path)
            else:
                self.right_pane._decompress_file(file_path)