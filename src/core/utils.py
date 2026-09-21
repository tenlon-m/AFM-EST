#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
包含各种通用工具函数
"""

from .logger import logger

def format_size(size):
    """
    格式化文件大小，根据实际大小自动选择合适单位
    
    Args:
        size: 文件大小（字节）
        
    Returns:
        格式化后的大小字符串
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size/1024:.2f} KB"
    elif size < 1024**3:
        return f"{size/(1024**2):.2f} MB"
    else:
        return f"{size/(1024**3):.2f} GB"

def detect_file_encoding(file_path):
    """
    检测文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件编码字符串
    """
    try:
        # 读取文件前几个字节，用于检测BOM和编码
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)  # 读取更多数据以提高检测准确性
    
        # 检测BOM（字节顺序标记）
        if raw_data.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'  # UTF-8 with BOM
        elif raw_data.startswith(b'\xff\xfe'):
            return 'utf-16-le'  # UTF-16 little-endian with BOM
        elif raw_data.startswith(b'\xfe\xff'):
            return 'utf-16-be'  # UTF-16 big-endian with BOM
        elif raw_data.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'  # UTF-32 little-endian
        elif raw_data.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'  # UTF-32 big-endian
    
        # 尝试使用chardet检测编码，并考虑置信度
        try:
            import chardet
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            # 只有置信度较高时才直接返回
            if encoding and confidence > 0.8:
                # 修复：将utf-16转换为具体的变体
                if encoding.lower() == 'utf-16':
                    # 尝试检测是le还是be
                    try:
                        raw_data.decode('utf-16-le')
                        return 'utf-16-le'
                    except UnicodeDecodeError:
                        return 'utf-16-be'
                return encoding
        except ImportError:
            # chardet不可用，继续使用内置方法
            pass
            
        # 尝试常用编码，按优先级顺序
        # 通用场景优先级：UTF-8 > UTF-16-le > UTF-16-be > GB18030 > GBK > Big5 > ISO-8859-1 > ASCII
        # 中文专属场景优先级：GB18030 > GBK > GB2312 > Big5
        # 老旧系统场景优先级：ISO-8859-1（Latin-1） > Shift_JIS > EUC-KR > ASCII
        # 综合优先级顺序，涵盖主要场景
        encodings = [
            'utf-8', 'utf-16-le', 'utf-16-be', 'gb18030', 'gbk', 'gb2312', 
            'big5', 'iso-8859-1', 'shift_jis', 'euc-kr', 'ascii'
        ]
        
        for encoding in encodings:
            try:
                # 使用原始数据进行解码测试，避免重复打开文件
                raw_data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        return 'utf-8'
    except Exception as e:
        logger.debug(f"操作失败: {e}")
        return 'utf-8'

def format_time(timestamp):
    """
    格式化日期时间
    
    Args:
        timestamp: 时间戳
        
    Returns:
        格式化后的日期时间字符串
    """
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def get_folder_size(folder_path):
    """
    计算文件夹大小
    
    Args:
        folder_path: 文件夹路径
        
    Returns:
        文件夹大小（字节）
    """
    import os
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except (FileNotFoundError, PermissionError, OSError):
                    # 跳过无法访问的文件
                    continue
    except (FileNotFoundError, PermissionError, OSError):
        # 跳过无法访问的文件夹
        pass
    return total_size

def get_unique_path(directory, original_name):
    """
    生成唯一路径，如果文件/文件夹已存在，则添加"副本"或"副本X"后缀
    
    Args:
        directory: 目标目录
        original_name: 原始文件名/文件夹名
        
    Returns:
        唯一的目标路径
    """
    import os
    # 检查原始路径是否存在
    full_path = os.path.join(directory, original_name)
    if not os.path.exists(full_path):
        return full_path
    
    # 分离文件名和扩展名
    if '.' in original_name:
        name_part, ext_part = original_name.rsplit('.', 1)
        ext_part = '.' + ext_part
    else:
        name_part = original_name
        ext_part = ''
    
    # 尝试 "原始名称 副本"
    candidate_name = f"{name_part} 副本{ext_part}"
    candidate_path = os.path.join(directory, candidate_name)
    if not os.path.exists(candidate_path):
        return candidate_path
    
    # 如果 "副本" 已存在，则尝试 "副本1", "副本2", ...
    i = 1
    while True:
        candidate_name = f"{name_part} 副本{i}{ext_part}"
        candidate_path = os.path.join(directory, candidate_name)
        if not os.path.exists(candidate_path):
            return candidate_path
        i += 1

# 尝试导入QMessageBox，如果失败则不显示消息框
QMessageBox = None
QApplication = None
QWidget = None
try:
    from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton
    from PySide6.QtCore import Qt
except ImportError:
    QMessageBox = None

class CopyableMessageBox(QDialog):
    """
    可复制的消息框
    支持右键复制错误信息
    """
    
    def __init__(self, parent, title, message, icon=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 200)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建文本编辑框，用于显示消息
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(message)
        self.text_edit.setReadOnly(True)
        self.text_edit.setContextMenuPolicy(Qt.DefaultContextMenu)  # 启用右键菜单
        layout.addWidget(self.text_edit)
        
        # 创建按钮
        button_layout = QVBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

def show_message_box(parent=None, title="", message="", icon="warning", buttons="ok"):
    """
    显示可复制的消息框
    
    Args:
        parent: 父窗口
        title: 消息框标题
        message: 消息内容
        icon: 图标类型（warning, error, information, question）
        buttons: 按钮类型（ok, yesno, yesnocancel）
        
    Returns:
        按钮点击结果
    """
    try:
        if not QMessageBox or not QApplication.instance():
            # 没有QApplication实例，只记录日志
            from .logger import logger
            logger.info(f"{title}: {message}")
            return "ok"
        
        # 图标映射
        icon_map = {
            "warning": QMessageBox.Warning,
            "error": QMessageBox.Critical,
            "information": QMessageBox.Information,
            "question": QMessageBox.Question
        }
        msg_icon = icon_map.get(icon, QMessageBox.Warning)
        
        # 按钮映射
        button_map = {
            "ok": QMessageBox.Ok,
            "yesno": QMessageBox.Yes | QMessageBox.No,
            "yesnocancel": QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        }
        msg_buttons = button_map.get(buttons, QMessageBox.Ok)
        
        # 对于警告和错误，使用可复制的消息框
        if icon in ["warning", "error"]:
            dialog = CopyableMessageBox(parent, title, message)
            result = dialog.exec()
            return "ok"
        else:
            # 对于其他类型，使用标准消息框
            result = QMessageBox.warning(parent, title, message, msg_buttons)
            
            # 结果映射
            result_map = {
                QMessageBox.Ok: "ok",
                QMessageBox.Yes: "yes",
                QMessageBox.No: "no",
                QMessageBox.Cancel: "cancel"
            }
            return result_map.get(result, "ok")
    except Exception as e:
        # 显示消息框失败，记录日志
        from .logger import logger
        logger.error(f"显示消息框失败: {e}")
        return "ok"

def show_warning(parent=None, title="警告", message=""):
    """
    显示警告消息框
    
    Args:
        parent: 父窗口
        title: 消息框标题
        message: 消息内容
        
    Returns:
        按钮点击结果
    """
    return show_message_box(parent, title, message, "warning", "ok")

def show_error(parent=None, title="错误", message=""):
    """
    显示错误消息框
    
    Args:
        parent: 父窗口
        title: 消息框标题
        message: 消息内容
        
    Returns:
        按钮点击结果
    """
    return show_message_box(parent, title, message, "error", "ok")

def show_info(parent=None, title="信息", message=""):
    """
    显示信息消息框
    
    Args:
        parent: 父窗口
        title: 消息框标题
        message: 消息内容
        
    Returns:
        按钮点击结果
    """
    return show_message_box(parent, title, message, "information", "ok")

def show_question(parent=None, title="询问", message="", buttons="yesno"):
    """
    显示询问消息框
    
    Args:
        parent: 父窗口
        title: 消息框标题
        message: 消息内容
        buttons: 按钮类型（yesno, yesnocancel）
        
    Returns:
        按钮点击结果（yes, no, cancel）
    """
    return show_message_box(parent, title, message, "question", buttons)
