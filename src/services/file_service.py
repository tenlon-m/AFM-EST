#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作服务模块
负责处理文件系统的各种操作
"""

import os
import shutil
import stat
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from concurrent.futures import Future
from core.logger import logger
from core.thread_pool import thread_pool_manager

try:
    from .directory_index_cache import directory_index_cache
    HAS_DIRECTORY_CACHE = True
except ImportError:
    HAS_DIRECTORY_CACHE = False

try:
    from .file_metadata_cache import get_file_metadata_cache
    HAS_METADATA_CACHE = True
    file_metadata_cache = get_file_metadata_cache()
except ImportError:
    HAS_METADATA_CACHE = False
    file_metadata_cache = None

class FileService:
    """
    文件操作服务类
    提供各种文件系统操作功能
    """
    
    @staticmethod
    def get_files_in_directory(path: str, show_hidden: bool = False, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取目录中的文件列表（支持缓存加速）
        
        Args:
            path: 目录路径
            show_hidden: 是否显示隐藏文件
            use_cache: 是否使用缓存
            
        Returns:
            文件列表，每个文件包含名称、路径、类型、大小、修改时间等信息
        """
        if use_cache and HAS_DIRECTORY_CACHE:
            cached_files = directory_index_cache.get_cached_directory(path)
            if cached_files is not None:
                if not show_hidden:
                    cached_files = [f for f in cached_files if not f["name"].startswith('.')]
                return cached_files
        
        files = []
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if not show_hidden and entry.name.startswith('.'):
                        continue
                    
                    try:
                        file_path = entry.path
                        
                        if HAS_METADATA_CACHE and file_metadata_cache:
                            metadata = file_metadata_cache.get_metadata(file_path)
                            if metadata:
                                file_info = {
                                    "name": entry.name,
                                    "path": file_path,
                                    "is_dir": metadata["is_dir"],
                                    "type": "文件夹" if metadata["is_dir"] else "文件",
                                    "size": metadata["size"],
                                    "mtime": metadata["mtime"],
                                    "ctime": metadata["ctime"],
                                    "atime": metadata["atime"],
                                    "mode": metadata["mode"]
                                }
                            else:
                                stat_info = entry.stat(follow_symlinks=False)
                                file_info = {
                                    "name": entry.name,
                                    "path": file_path,
                                    "is_dir": entry.is_dir(follow_symlinks=False),
                                    "type": "文件夹" if entry.is_dir(follow_symlinks=False) else "文件",
                                    "size": stat_info.st_size,
                                    "mtime": stat_info.st_mtime,
                                    "ctime": stat_info.st_ctime,
                                    "atime": stat_info.st_atime,
                                    "mode": stat_info.st_mode
                                }
                                file_metadata_cache.cache_metadata(file_path, stat_info)
                        else:
                            stat_info = entry.stat(follow_symlinks=False)
                            file_info = {
                                "name": entry.name,
                                "path": file_path,
                                "is_dir": entry.is_dir(follow_symlinks=False),
                                "type": "文件夹" if entry.is_dir(follow_symlinks=False) else "文件",
                                "size": stat_info.st_size,
                                "mtime": stat_info.st_mtime,
                                "ctime": stat_info.st_ctime,
                                "atime": stat_info.st_atime,
                                "mode": stat_info.st_mode
                            }
                        files.append(file_info)
                    except Exception as e:
                        logger.error(f"获取文件信息失败: {entry.path}, 错误: {e}")
            
            if HAS_DIRECTORY_CACHE:
                directory_index_cache.cache_directory(path, files)
        except Exception as e:
            logger.error(f"读取目录失败: {path}, 错误: {e}")
        
        return files
    
    @staticmethod
    def get_files_in_directory_async(path: str, show_hidden: bool = False, 
                                     callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None) -> Future:
        """
        异步获取目录中的文件列表
        使用线程池避免阻塞主线程
        
        Args:
            path: 目录路径
            show_hidden: 是否显示隐藏文件
            callback: 完成回调函数，接收文件列表参数
            
        Returns:
            Future对象，可通过result()获取文件列表
        """
        def task():
            result = FileService.get_files_in_directory(path, show_hidden)
            if callback:
                callback(result)
            return result
        
        future = thread_pool_manager.submit(task)
        logger.debug(f"异步目录扫描任务已提交: {path}")
        return future
    
    @staticmethod
    def is_file_locked(file_path: str) -> bool:
        """
        检测文件是否被占用
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否被占用
        """
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False
        
        try:
            with open(file_path, 'a+b') as f:
                f.flush()
                os.fsync(f.fileno())
            return False
        except (PermissionError, IOError, OSError):
            return True
    
    @staticmethod
    def check_disk_space(path: str, required_size: int) -> bool:
        """
        检查磁盘空间是否足够
        
        Args:
            path: 检查的路径
            required_size: 需要的空间大小（字节）
            
        Returns:
            磁盘空间是否足够
        """
        try:
            usage = shutil.disk_usage(path)
            return usage.free >= required_size
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")
            return False
    
    @staticmethod
    def copy_files(src_paths: List[str], dest_dir: str) -> bool:
        """
        复制文件或文件夹到目标目录
        
        Args:
            src_paths: 源文件或文件夹路径列表
            dest_dir: 目标目录路径
            
        Returns:
            操作是否成功
        """
        try:
            for src_path in src_paths:
                src = Path(src_path)
                dest = Path(dest_dir) / src.name
                
                # 检查目标目录磁盘空间
                if src.is_dir():
                    required_size = FileService.get_folder_size(src_path)
                else:
                    required_size = src.stat().st_size
                
                if not FileService.check_disk_space(dest_dir, required_size):
                    logger.error(f"磁盘空间不足: {dest_dir}")
                    return False
                
                # 检查源文件是否被占用
                if src.is_file() and FileService.is_file_locked(src_path):
                    logger.error(f"源文件被占用: {src_path}")
                    return False
                
                if src.is_dir():
                    shutil.copytree(src, dest)
                    logger.info(f"复制文件夹成功: {src} -> {dest}")
                else:
                    shutil.copy2(src, dest)
                    logger.info(f"复制文件成功: {src} -> {dest}")
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def move_files(src_paths: List[str], dest_dir: str) -> bool:
        """
        移动文件或文件夹到目标目录
        
        Args:
            src_paths: 源文件或文件夹路径列表
            dest_dir: 目标目录路径
            
        Returns:
            操作是否成功
        """
        try:
            for src_path in src_paths:
                src = Path(src_path)
                dest = Path(dest_dir) / src.name
                
                # 检查目标目录磁盘空间
                if src.is_dir():
                    required_size = FileService.get_folder_size(src_path)
                else:
                    required_size = src.stat().st_size
                
                if not FileService.check_disk_space(dest_dir, required_size):
                    logger.error(f"磁盘空间不足: {dest_dir}")
                    return False
                
                # 检查源文件是否被占用
                if src.is_file() and FileService.is_file_locked(src_path):
                    logger.error(f"源文件被占用: {src_path}")
                    return False
                
                shutil.move(src, dest)
                logger.info(f"移动文件成功: {src} -> {dest}")
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            return False
    
    @staticmethod
    def delete_files(file_paths: List[str], recursive: bool = False) -> bool:
        """
        删除文件或文件夹
        
        Args:
            file_paths: 要删除的文件或文件夹路径列表
            recursive: 是否递归删除文件夹
            
        Returns:
            操作是否成功
        """
        try:
            for file_path in file_paths:
                path = Path(file_path)
                if path.is_dir():
                    # 检查文件夹内文件是否被占用
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            if FileService.is_file_locked(file_full_path):
                                logger.error(f"文件被占用: {file_full_path}")
                                return False
                    shutil.rmtree(path, ignore_errors=True)
                    logger.info(f"删除文件夹成功: {path}")
                else:
                    # 检查文件是否被占用
                    if FileService.is_file_locked(file_path):
                        logger.error(f"文件被占用: {file_path}")
                        return False
                    path.unlink()
                    logger.info(f"删除文件成功: {path}")
            
            if HAS_DIRECTORY_CACHE:
                for file_path in file_paths:
                    directory_index_cache.invalidate_cache(str(Path(file_path).parent))
            
            if HAS_METADATA_CACHE and file_metadata_cache:
                for file_path in file_paths:
                    file_metadata_cache.invalidate_cache(file_path)
            
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    @staticmethod
    def rename_file(src_path: str, new_name: str) -> bool:
        """
        重命名文件或文件夹
        
        Args:
            src_path: 源文件或文件夹路径
            new_name: 新名称
            
        Returns:
            操作是否成功
        """
        try:
            src = Path(src_path)
            dest = src.parent / new_name
            
            # 检查文件是否被占用
            if src.is_file() and FileService.is_file_locked(src_path):
                logger.error(f"文件被占用: {src_path}")
                return False
            
            src.rename(dest)
            logger.info(f"重命名成功: {src} -> {dest}")
            
            if HAS_DIRECTORY_CACHE:
                directory_index_cache.invalidate_cache(str(src.parent))
            
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"重命名失败: {e}")
            return False
    
    @staticmethod
    def create_directory(path: str) -> bool:
        """
        创建目录
        
        Args:
            path: 目录路径
            
        Returns:
            操作是否成功
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录成功: {path}")
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False
    
    @staticmethod
    def create_file(path: str) -> bool:
        """
        创建文件
        
        Args:
            path: 文件路径
            
        Returns:
            操作是否成功
        """
        try:
            # 确保父目录存在
            parent_dir = Path(path).parent
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            
            Path(path).touch(exist_ok=True)
            logger.info(f"创建文件成功: {path}")
            return True
        except PermissionError as e:
            logger.error(f"权限不足: {e}")
            return False
        except Exception as e:
            logger.error(f"创建文件失败: {e}")
            return False
    
    @staticmethod
    def get_file_properties(path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件或文件夹的属性
        
        Args:
            path: 文件或文件夹路径
            
        Returns:
            文件属性字典，包含大小、修改时间、创建时间等信息
        """
        try:
            stat_info = os.stat(path)
            path_obj = Path(path)
            
            properties = {
                "name": path_obj.name,
                "path": str(path_obj),
                "is_dir": path_obj.is_dir(),
                "size": stat_info.st_size,
                "mtime": stat_info.st_mtime,
                "ctime": stat_info.st_ctime,
                "atime": stat_info.st_atime,
                "mode": stat_info.st_mode,
                "permissions": stat.filemode(stat_info.st_mode),
                "inode": stat_info.st_ino,
                "dev": stat_info.st_dev,
                "nlink": stat_info.st_nlink,
                "uid": stat_info.st_uid,
                "gid": stat_info.st_gid
            }
            
            return properties
        except Exception as e:
            logger.error(f"获取文件属性失败: {path}, 错误: {e}")
            return None
    
    @staticmethod
    def get_disk_usage(drive: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        获取磁盘使用情况
        
        Args:
            drive: 驱动器路径，如 "C:" 或 "/"
            
        Returns:
            (总大小, 已用大小, 可用大小)，单位为字节
        """
        try:
            usage = shutil.disk_usage(drive)
            return usage.total, usage.used, usage.free
        except Exception as e:
            logger.error(f"获取磁盘使用情况失败: {drive}, 错误: {e}")
            return None, None, None
    
    @staticmethod
    def get_available_drives() -> List[str]:
        """
        获取可用的驱动器列表
        
        Returns:
            驱动器路径列表
        """
        drives = []
        if os.name == 'nt':  # Windows
            import win32api
            try:
                # win32api.GetLogicalDriveStrings() 返回格式为 "C:\\0D:\\0E:\\0" 或 "C:\\D:\\E:\\"
                drive_strings = win32api.GetLogicalDriveStrings()
                # 使用空字符分割（适用于 "C:\\0D:\\0E:\\0" 格式）
                if '\0' in drive_strings:
                    drive_list = [d for d in drive_strings.split('\0') if d.strip()]
                else:
                    # 兼容其他格式
                    drive_list = [d for d in drive_strings.split('\\') if d.strip() and ':' in d]
                
                drives = []
                for drive in drive_list:
                    # 确保驱动器格式正确，如 "C:\" 或 "C:" -> "C:\"
                    if len(drive) >= 2 and drive[1] == ':':
                        drive_letter = drive[0].upper()
                        drives.append(f"{drive_letter}:\\")
            except Exception as e:
                logger.error(f"获取Windows驱动器列表失败: {e}")
        else:  # Linux/macOS
            try:
                drives = ["/"]  # 默认根目录
                # 可以添加更多逻辑来获取挂载的设备
            except Exception as e:
                logger.error(f"获取Linux/macOS驱动器列表失败: {e}")
        
        return drives
    
    @staticmethod
    def is_hidden(file_path: str) -> bool:
        """
        检查文件或文件夹是否为隐藏
        
        Args:
            file_path: 文件或文件夹路径
            
        Returns:
            是否为隐藏文件
        """
        path = Path(file_path)
        if path.name.startswith('.'):
            return True
        
        if os.name == 'nt':  # Windows
            import win32api
            import win32con
            try:
                attr = win32api.GetFileAttributes(file_path)
                return bool(attr & win32con.FILE_ATTRIBUTE_HIDDEN)
            except Exception as e:
                logger.error(f"检查Windows文件隐藏属性失败: {file_path}, 错误: {e}")
                return False
        
        return False
    
    @staticmethod
    def set_hidden(file_path: str, hidden: bool) -> bool:
        """
        设置文件或文件夹的隐藏属性
        
        Args:
            file_path: 文件或文件夹路径
            hidden: 是否设置为隐藏
            
        Returns:
            操作是否成功
        """
        if os.name == 'nt':  # Windows
            import win32api
            import win32con
            try:
                attr = win32api.GetFileAttributes(file_path)
                if hidden:
                    win32api.SetFileAttributes(file_path, attr | win32con.FILE_ATTRIBUTE_HIDDEN)
                else:
                    win32api.SetFileAttributes(file_path, attr & ~win32con.FILE_ATTRIBUTE_HIDDEN)
                return True
            except Exception as e:
                logger.error(f"设置Windows文件隐藏属性失败: {file_path}, 错误: {e}")
                return False
        else:  # Linux/macOS
            path = Path(file_path)
            if hidden and not path.name.startswith('.'):
                new_path = path.parent / f".{path.name}"
                path.rename(new_path)
                return True
            elif not hidden and path.name.startswith('.'):
                new_path = path.parent / path.name[1:]
                path.rename(new_path)
                return True
        
        return True
    
    @staticmethod
    def get_folder_size(folder_path: str) -> int:
        """
        计算文件夹大小
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            文件夹大小（字节）
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except (FileNotFoundError, PermissionError, OSError):
                        continue
        except (FileNotFoundError, PermissionError, OSError):
            pass
        return total_size
    
    @staticmethod
    def format_size(size: int) -> str:
        """
        格式化文件大小，转换为人类可读的格式
        
        Args:
            size: 文件大小，单位为字节
            
        Returns:
            格式化后的大小字符串
        """
        if size < 0:
            return "-"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        
        return f"{size:.2f} PB"

# 创建文件服务实例
file_service = FileService()
