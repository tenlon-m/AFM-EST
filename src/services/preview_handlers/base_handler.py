#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览处理器基类
定义所有预览处理器的统一接口
"""

from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget


class PreviewHandler(ABC):
    """
    预览处理器基类
    所有类型的文件预览处理器都必须继承此类
    """
    
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否能处理指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否能处理
        """
        pass
    
    @abstractmethod
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成文件预览
        
        Args:
            file_path: 文件路径
            parent_widget: 父组件
            
        Returns:
            QWidget: 预览组件
        """
        pass
