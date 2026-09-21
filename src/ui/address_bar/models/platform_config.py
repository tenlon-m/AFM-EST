#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台配置数据模型
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from PySide6.QtGui import QIcon
import os


class PlatformType(Enum):
    """平台类型枚举"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


@dataclass
class PlatformConfig:
    """
    平台配置数据模型
    存储特定平台的地址栏显示配置
    """
    platform_type: PlatformType
    root_node_name: str  # 根节点名称（"此电脑"/"计算机"/"Macintosh HD"）
    root_node_icon: Optional[QIcon] = None  # 根节点图标
    path_separator: str = ">"  # 面包屑分隔符
    native_separator: str = "\\"  # 原生路径分隔符
    is_case_sensitive: bool = False  # 是否区分大小写
    
    @classmethod
    def from_platform(cls, platform: str) -> 'PlatformConfig':
        """
        根据平台类型创建配置
        
        Args:
            platform: 平台名称（"windows"/"linux"/"darwin"）
            
        Returns:
            PlatformConfig: 平台配置对象
        """
        if platform == "windows":
            return cls(
                platform_type=PlatformType.WINDOWS,
                root_node_name="此电脑",
                path_separator=">",
                native_separator="\\",
                is_case_sensitive=False
            )
        elif platform == "linux":
            return cls(
                platform_type=PlatformType.LINUX,
                root_node_name="计算机",
                path_separator=">",
                native_separator="/",
                is_case_sensitive=True
            )
        elif platform == "darwin":
            return cls(
                platform_type=PlatformType.MACOS,
                root_node_name="Macintosh HD",
                path_separator=">",
                native_separator="/",
                is_case_sensitive=False
            )
        else:
            # 默认使用Linux配置
            return cls(
                platform_type=PlatformType.LINUX,
                root_node_name="计算机",
                path_separator=">",
                native_separator="/",
                is_case_sensitive=True
            )
    
    @classmethod
    def auto_detect(cls) -> 'PlatformConfig':
        """
        自动检测当前平台并创建配置
        
        Returns:
            PlatformConfig: 平台配置对象
        """
        if os.name == "nt":
            return cls.from_platform("windows")
        elif os.name == "posix":
            import sys
            if sys.platform == "darwin":
                return cls.from_platform("darwin")
            else:
                return cls.from_platform("linux")
        else:
            return cls.from_platform("linux")