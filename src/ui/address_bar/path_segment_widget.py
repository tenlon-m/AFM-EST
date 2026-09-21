#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径段组件
Windows 11风格的地址栏路径段
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal


class PathSegmentWidget(QWidget):
    """
    路径段组件
    表示地址栏中的一个路径段（如"Users"、"Administrator"等）
    """
    
    clicked = Signal()  # 点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._label_text = ""
        self._path = ""
        self._is_current = False  # 是否为当前路径
        self._is_hovered = False
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        
        # 文本标签
        self._text_label = QLabel()
        self._text_label.setObjectName("pathSegmentText")
        layout.addWidget(self._text_label)
        
        # 设置组件属性
        self.setObjectName("pathSegmentWidget")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(20)
    
    def _apply_style(self):
        """应用样式"""
        self._update_style()
    
    def _update_style(self):
        """更新样式"""
        if self._is_current:
            # 当前路径段 - 加粗显示
            font_weight = "bold"
            if self._is_hovered:
                bg_color = "rgba(0, 120, 212, 0.1)"
                text_color = "#0078D4"
            else:
                bg_color = "transparent"
                text_color = "#000000"
        elif self._is_hovered:
            # 悬停状态
            font_weight = "normal"
            bg_color = "rgba(0, 0, 0, 0.05)"
            text_color = "#000000"
        else:
            # 默认状态
            font_weight = "normal"
            bg_color = "transparent"
            text_color = "#000000"
        
        style = f"""
            #pathSegmentWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
            }}
            #pathSegmentText {{
                color: {text_color};
                background: transparent;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 9pt;
                font-weight: {font_weight};
            }}
        """
        self.setStyleSheet(style)
    
    def set_text(self, text: str):
        """
        设置显示文本
        
        Args:
            text: 显示文本
        """
        self._label_text = text
        self._text_label.setText(text)
    
    def set_path(self, path: str):
        """
        设置路径
        
        Args:
            path: 完整路径
        """
        self._path = path
    
    def get_path(self) -> str:
        """获取路径"""
        return self._path
    
    def set_current(self, is_current: bool):
        """
        设置是否为当前路径
        
        Args:
            is_current: 是否为当前路径
        """
        self._is_current = is_current
        self._update_style()
    
    def is_current(self) -> bool:
        """是否为当前路径"""
        return self._is_current
    
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
            if self._is_current:
                font_weight = "bold"
                if self._is_hovered:
                    bg_color = "rgba(0, 120, 212, 0.2)"
                    text_color = "#60CDFF"
                else:
                    bg_color = "transparent"
                    text_color = "#FFFFFF"
            elif self._is_hovered:
                font_weight = "normal"
                bg_color = "rgba(255, 255, 255, 0.05)"
                text_color = "#FFFFFF"
            else:
                font_weight = "normal"
                bg_color = "transparent"
                text_color = "#FFFFFF"
        else:
            # 浅色主题
            if self._is_current:
                font_weight = "bold"
                if self._is_hovered:
                    bg_color = "rgba(0, 120, 212, 0.1)"
                    text_color = "#0078D4"
                else:
                    bg_color = "transparent"
                    text_color = "#000000"
            elif self._is_hovered:
                font_weight = "normal"
                bg_color = "rgba(0, 0, 0, 0.05)"
                text_color = "#000000"
            else:
                font_weight = "normal"
                bg_color = "transparent"
                text_color = "#000000"
        
        style = f"""
            #pathSegmentWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
            }}
            #pathSegmentText {{
                color: {text_color};
                background: transparent;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 9pt;
                font-weight: {font_weight};
            }}
        """
        self.setStyleSheet(style)