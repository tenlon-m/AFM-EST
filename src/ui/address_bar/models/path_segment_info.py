#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径段信息数据模型
"""

from dataclasses import dataclass
from typing import Optional
from PySide6.QtGui import QIcon


@dataclass
class PathSegmentInfo:
    """
    路径段信息数据模型
    表示地址栏中的一个路径段（如"本地磁盘 (C:)"、"Users"等）
    """
    name: str  # 显示名称
    path: str  # 完整路径
    is_root: bool = False  # 是否为根节点（此电脑/计算机）
    icon: Optional[QIcon] = None  # 图标（可选）
    
    def __post_init__(self):
        """初始化后验证"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("路径段名称不能为空且必须为字符串")
        
        # 根节点允许路径为空
        if not self.is_root:
            if not self.path or not isinstance(self.path, str):
                raise ValueError("路径不能为空且必须为字符串")
    
    def __str__(self) -> str:
        """字符串表示"""
        return self.name
    
    def __repr__(self) -> str:
        """调试表示"""
        return f"PathSegmentInfo(name='{self.name}', path='{self.path}', is_root={self.is_root})"