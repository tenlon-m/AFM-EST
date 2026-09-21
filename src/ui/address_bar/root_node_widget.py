#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根节点组件
Windows 11风格的地址栏根节点（此电脑/计算机）
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap


class RootNodeWidget(QWidget):
    """
    根节点组件
    表示地址栏中的根节点（此电脑/计算机/Macintosh HD）
    """
    
    clicked = Signal()  # 点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._label_text = ""
        self._is_highlight = False
        self._is_hovered = False
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        # 图标标签
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(16, 16)
        layout.addWidget(self._icon_label)
        
        # 文本标签
        self._text_label = QLabel()
        self._text_label.setObjectName("rootNodeText")
        layout.addWidget(self._text_label)
        
        # 设置组件属性
        self.setObjectName("rootNodeWidget")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(20)
    
    def _apply_style(self):
        """应用样式"""
        self._update_style()
    
    def _update_style(self):
        """更新样式"""
        if self._is_highlight:
            bg_color = "rgba(0, 120, 212, 0.1)"
            text_color = "#0078D4"
        elif self._is_hovered:
            bg_color = "rgba(0, 0, 0, 0.05)"
            text_color = "#000000"
        else:
            bg_color = "transparent"
            text_color = "#000000"
        
        style = f"""
            #rootNodeWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
            }}
            #rootNodeText {{
                color: {text_color};
                background: transparent;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 9pt;
            }}
        """
        self.setStyleSheet(style)
    
    def set_label(self, text: str):
        """
        设置显示文本
        
        Args:
            text: 显示文本
        """
        self._label_text = text
        self._text_label.setText(text)
    
    def set_icon(self, icon: QIcon):
        """
        设置图标
        
        Args:
            icon: 图标对象
        """
        if icon and not icon.isNull():
            pixmap = icon.pixmap(16, 16)
            self._icon_label.setPixmap(pixmap)
        else:
            self._icon_label.clear()
    
    def set_icon_from_file(self, icon_path: str):
        """
        从文件设置图标
        
        Args:
            icon_path: 图标文件路径
        """
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self._icon_label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._icon_label.clear()
    
    def set_highlight(self, highlight: bool):
        """
        设置高亮状态
        
        Args:
            highlight: 是否高亮
        """
        self._is_highlight = highlight
        self._update_style()
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovered = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def apply_theme(self, theme_name: str):
        """
        应用主题
        
        Args:
            theme_name: 主题名称（"light"或"dark"）
        """
        if theme_name == "dark":
            # 深色主题
            if self._is_highlight:
                bg_color = "rgba(0, 120, 212, 0.2)"
                text_color = "#60CDFF"
            elif self._is_hovered:
                bg_color = "rgba(255, 255, 255, 0.05)"
                text_color = "#FFFFFF"
            else:
                bg_color = "transparent"
                text_color = "#FFFFFF"
        else:
            # 浅色主题
            if self._is_highlight:
                bg_color = "rgba(0, 120, 212, 0.1)"
                text_color = "#0078D4"
            elif self._is_hovered:
                bg_color = "rgba(0, 0, 0, 0.05)"
                text_color = "#000000"
            else:
                bg_color = "transparent"
                text_color = "#000000"
        
        style = f"""
            #rootNodeWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
            }}
            #rootNodeText {{
                color: {text_color};
                background: transparent;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 9pt;
            }}
        """
        self.setStyleSheet(style)