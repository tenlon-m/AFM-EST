#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导航模式枚举
"""

from enum import Enum


class NavigationMode(Enum):
    """
    导航模式枚举
    定义地址栏的两种显示模式
    """
    BREADCRUMB = "breadcrumb"  # 面包屑导航模式（默认）
    EDIT = "edit"  # 路径编辑模式
    
    def __str__(self) -> str:
        """字符串表示"""
        return self.value
    
    def __repr__(self) -> str:
        """调试表示"""
        return f"NavigationMode.{self.name}"