#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台适配器
处理跨平台路径和配置适配
"""

import os
from pathlib import Path
from typing import Optional, List
from .models.platform_config import PlatformConfig, PlatformType
from .models.path_segment_info import PathSegmentInfo


class PlatformAdapter:
    """
    平台适配器（单例模式）
    提供跨平台的路径处理和配置管理
    """
    
    _instance: Optional['PlatformAdapter'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._platform_config = PlatformConfig.auto_detect()
        self._localization_cache = {}
        self._drive_name_cache = {}  # 驱动器名称缓存
    
    @property
    def platform_config(self) -> PlatformConfig:
        """获取平台配置"""
        return self._platform_config
    
    @property
    def platform_type(self) -> PlatformType:
        """获取平台类型"""
        return self._platform_config.platform_type
    
    def normalize_path(self, path: str) -> str:
        """
        规范化路径
        
        Args:
            path: 原始路径
            
        Returns:
            str: 规范化后的路径
        """
        if not path:
            return path
        
        # 使用pathlib规范化
        try:
            normalized = str(Path(path).resolve())
            return normalized
        except Exception:
            return path
    
    def is_path_valid(self, path: str) -> bool:
        """
        验证路径是否有效
        
        Args:
            path: 路径
            
        Returns:
            bool: 路径是否有效
        """
        if not path:
            return False
        
        try:
            p = Path(path)
            
            # 检查路径是否存在
            if not p.exists():
                return False
            
            # 检查路径是否可访问
            if not os.access(path, os.R_OK):
                return False
            
            return True
        except (OSError, ValueError):
            return False
    
    def get_root_node_name(self) -> str:
        """
        获取根节点名称
        
        Returns:
            str: 根节点名称
        """
        return self._platform_config.root_node_name
    
    def get_path_separator(self) -> str:
        """
        获取面包屑分隔符
        
        Returns:
            str: 分隔符
        """
        return self._platform_config.path_separator
    
    def get_native_separator(self) -> str:
        """
        获取原生路径分隔符
        
        Returns:
            str: 原生分隔符
        """
        return self._platform_config.native_separator
    
    def parse_path_to_segments(self, path: str) -> List[PathSegmentInfo]:
        """
        将路径解析为路径段列表
        
        Args:
            path: 完整路径
            
        Returns:
            List[PathSegmentInfo]: 路径段列表
        """
        segments = []
        
        if not path:
            return segments
        
        # 添加根节点
        root_name = self.get_root_node_name()
        segments.append(PathSegmentInfo(
            name=root_name,
            path="",
            is_root=True
        ))
        
        # 解析路径段
        try:
            p = Path(path)
            parts = list(p.parts)
            
            # 处理不同平台的根路径
            if self.platform_type == PlatformType.WINDOWS:
                # Windows: ['C:\\', 'Users', 'Administrator']
                if parts and len(parts[0]) == 3 and parts[0][1] == ':':
                    # 驱动器号（如 C:\）
                    drive = parts[0]
                    drive_name = self._get_drive_display_name(drive)
                    segments.append(PathSegmentInfo(
                        name=drive_name,
                        path=drive,
                        is_root=False
                    ))
                    parts = parts[1:]
                else:
                    drive = ""
            else:
                # Linux/macOS: ['/', 'home', 'user']
                if parts and parts[0] == '/':
                    parts = parts[1:]
                drive = ""
            
            # 添加路径段
            current_path = drive if self.platform_type == PlatformType.WINDOWS else "/"
            for i, part in enumerate(parts):
                if self.platform_type == PlatformType.WINDOWS:
                    current_path = os.path.join(current_path, part)
                else:
                    current_path = os.path.join(current_path, part)
                
                segments.append(PathSegmentInfo(
                    name=part,
                    path=current_path,
                    is_root=False
                ))
        
        except Exception:
            pass
        
        return segments
    
    def _get_drive_display_name(self, drive: str) -> str:
        """
        获取驱动器显示名称
        
        Args:
            drive: 驱动器路径（如 "C:\\"）
            
        Returns:
            str: 显示名称（如 "本地磁盘 (C:)"）
        """
        # 检查缓存
        if drive in self._drive_name_cache:
            return self._drive_name_cache[drive]
        
        try:
            import psutil
            partition_name = drive.rstrip("\\")
            
            for partition in psutil.disk_partitions():
                if partition.mountpoint.rstrip("\\") == partition_name:
                    # 获取卷标
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        label = partition.mountpoint
                        # 尝试获取卷标名称
                        if os.name == 'nt':
                            import ctypes
                            volume_name = ctypes.create_unicode_buffer(1024)
                            ctypes.windll.kernel32.GetVolumeInformationW(
                                ctypes.c_wchar_p(partition.mountpoint),
                                volume_name, 1024, None, None, None, None, 0
                            )
                            if volume_name.value:
                                result = f"{volume_name.value} ({drive[0]}:)"
                                self._drive_name_cache[drive] = result
                                return result
                    except Exception:
                        pass
                    
                    result = f"本地磁盘 ({drive[0]}:)"
                    self._drive_name_cache[drive] = result
                    return result
        except Exception:
            pass
        
        result = f"本地磁盘 ({drive[0]})"
        self._drive_name_cache[drive] = result
        return result


# 全局单例
platform_adapter = PlatformAdapter()