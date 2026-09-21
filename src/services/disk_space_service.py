#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
磁盘空间分析服务
负责分析磁盘空间占用情况，包括文件夹大小、大文件等
"""

import os
import threading
from typing import List, Dict

class DiskSpaceService:
    """
    磁盘空间分析服务类
    """
    
    def __init__(self):
        self.stop_event = threading.Event()
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收参数 (current, total, message)
        """
        self.progress_callback = callback
    
    def stop(self):
        """停止当前分析任务"""
        self.stop_event.set()
    
    def reset(self):
        """重置停止事件"""
        self.stop_event.clear()
    
    def format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            格式化后的字符串
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def get_disk_usage(self, drive_path: str) -> Dict:
        """
        获取磁盘使用情况
        
        Args:
            drive_path: 磁盘路径（如 "C:\\"）
            
        Returns:
            磁盘使用信息字典
        """
        try:
            total_bytes = 0
            free_bytes = 0
            
            if os.name == 'nt':
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    drive_path, None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
                )
                total_bytes = total_bytes.value
                free_bytes = free_bytes.value
            else:
                import shutil
                usage = shutil.disk_usage(drive_path)
                total_bytes = usage.total
                free_bytes = usage.free
            
            used_bytes = total_bytes - free_bytes
            
            return {
                'drive': drive_path,
                'total': total_bytes,
                'used': used_bytes,
                'free': free_bytes,
                'percent_used': (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0
            }
        except Exception:
            return {
                'drive': drive_path,
                'total': 0,
                'used': 0,
                'free': 0,
                'percent_used': 0
            }
    
    def calculate_folder_size(self, folder_path: str) -> int:
        """
        计算文件夹大小
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            文件夹大小（字节）
        """
        total_size = 0
        
        try:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    if self.stop_event.is_set():
                        return 0
                    
                    try:
                        if entry.is_symlink():
                            continue
                        
                        if entry.is_dir(follow_symlinks=False):
                            total_size += self.calculate_folder_size(entry.path)
                        else:
                            total_size += entry.stat(follow_symlinks=False).st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError) as e:
            logger.debug(f"计算文件夹大小失败: {folder_path}, 错误: {e}")
        
        return total_size
    
    def analyze_disk_folders(self, drive_path: str, max_depth: int = 2) -> List[Dict]:
        """
        分析磁盘上各文件夹的空间占用
        
        Args:
            drive_path: 磁盘路径（如 "C:\\"）
            max_depth: 分析深度
            
        Returns:
            文件夹空间占用列表
        """
        result = []
        total_count = 0
        processed_count = 0
        
        try:
            with os.scandir(drive_path) as entries:
                folders = [entry for entry in entries if entry.is_dir(follow_symlinks=False) and not entry.is_symlink()]
                total_count = len(folders)
            
            for entry in folders:
                if self.stop_event.is_set():
                    break
                
                try:
                    folder_name = entry.name
                    folder_path = entry.path
                    
                    if folder_name in ['System Volume Information', '$Recycle.Bin', 'ProgramData', 'Windows']:
                        continue
                    
                    folder_size = self.calculate_folder_size(folder_path)
                    
                    result.append({
                        'name': folder_name,
                        'path': folder_path,
                        'size': folder_size,
                        'type': 'folder'
                    })
                    
                    processed_count += 1
                    if self.progress_callback:
                        self.progress_callback(processed_count, total_count, f"分析文件夹: {folder_name}")
                        
                except (OSError, PermissionError):
                    continue
        
        except (OSError, PermissionError) as e:
            logger.debug(f"分析磁盘失败: {drive_path}, 错误: {e}")
        
        return result
    
    def analyze_large_files(self, drive_path: str, min_size_mb: int = 100) -> List[Dict]:
        """
        分析磁盘上的大文件
        
        Args:
            drive_path: 磁盘路径（如 "C:\\"）
            min_size_mb: 最小文件大小（MB）
            
        Returns:
            大文件列表
        """
        result = []
        min_size_bytes = min_size_mb * 1024 * 1024
        processed_count = 0
        
        try:
            for root, dirs, files in os.walk(drive_path):
                if self.stop_event.is_set():
                    break
                
                dirs[:] = [d for d in dirs if d not in ['System Volume Information', '$Recycle.Bin', 'ProgramData', 'Windows', '.git', 'node_modules']]
                
                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        try:
                            filesize = os.path.getsize(filepath)
                        except (OSError, PermissionError):
                            filesize = 0
                        
                        if filesize >= min_size_bytes:
                            result.append({
                                'name': filename,
                                'path': filepath,
                                'size': filesize,
                                'type': 'file'
                            })
                        
                        processed_count += 1
                        if self.progress_callback and processed_count % 1000 == 0:
                            self.progress_callback(processed_count, 0, f"扫描文件: {processed_count}")
                            
                    except (OSError, PermissionError):
                        continue
        
        except (OSError, PermissionError) as e:
            logger.debug(f"分析磁盘失败: {drive_path}, 错误: {e}")
        
        return result
    
    def analyze_specific_folder(self, folder_path: str) -> List[Dict]:
        """
        分析指定文件夹的空间占用
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            子文件夹空间占用列表
        """
        result = []
        total_count = 0
        processed_count = 0
        
        try:
            with os.scandir(folder_path) as entries:
                items = [entry for entry in entries if not entry.is_symlink()]
                total_count = len(items)
            
            for entry in items:
                if self.stop_event.is_set():
                    break
                
                try:
                    item_name = entry.name
                    item_path = entry.path
                    
                    if entry.is_dir(follow_symlinks=False):
                        item_size = self.calculate_folder_size(item_path)
                        item_type = 'folder'
                    else:
                        item_size = entry.stat(follow_symlinks=False).st_size
                        item_type = 'file'
                    
                    result.append({
                        'name': item_name,
                        'path': item_path,
                        'size': item_size,
                        'type': item_type
                    })
                    
                    processed_count += 1
                    if self.progress_callback:
                        self.progress_callback(processed_count, total_count, f"分析: {item_name}")
                        
                except (OSError, PermissionError):
                    continue
        
        except (OSError, PermissionError) as e:
            logger.debug(f"分析磁盘失败: {drive_path}, 错误: {e}")
        
        return result
    
    def sort_results(self, results: List[Dict], sort_by: str = 'size', ascending: bool = False) -> List[Dict]:
        """
        对分析结果进行排序
        
        Args:
            results: 分析结果列表
            sort_by: 排序字段（'size', 'name', 'type'）
            ascending: 是否升序排列
            
        Returns:
            排序后的结果列表
        """
        if sort_by == 'size':
            results.sort(key=lambda x: x['size'], reverse=not ascending)
        elif sort_by == 'name':
            results.sort(key=lambda x: x['name'], reverse=ascending)
        elif sort_by == 'type':
            results.sort(key=lambda x: x['type'], reverse=ascending)
        
        return results