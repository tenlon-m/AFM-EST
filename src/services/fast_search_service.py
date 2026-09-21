#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NTFS快速搜索服务
基于Windows API实现高效文件搜索

技术原理：
1. FindFirstFile/FindNextFile: Windows API快速文件枚举
2. 内存索引：将文件元数据加载到内存，实现毫秒级搜索
3. 并行扫描：多线程并行扫描多个盘符
4. 增量更新：通过USN Journal实时同步文件变更

注意：此功能仅支持Windows平台
"""


import os
import sys
import time
import struct
import fnmatch
import threading
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.logger import logger

# Windows API常量
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FSCTL_ENUM_USN_DATA = 0x000900B3
FSCTL_READ_USN_JOURNAL = 0x000900BB
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400

# 仅在Windows平台导入ctypes
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

# 跳过的系统目录
SKIP_DIRS = frozenset({
    'System Volume Information', 'Recycler', '$Recycle.Bin', 'ProgramData',
    'Windows', 'WinSxS', 'Documents and Settings', 'Program Files',
    'Program Files (x86)', 'boot', 'Recovery', '$Windows.~BT',
})

# 跳过的文件扩展名
SKIP_EXTENSIONS = frozenset({
    '.sys', '.dll', '.exe', '.com', '.bat', '.tmp', '.temp',
    '.lock', '.db', '.dat', '.bin', '.iso', '.msi', '.cab',
})


class NTFSSearchIndex:
    """
    NTFS文件系统索引类
    负责构建和维护文件索引
    
    优化数据结构：
    - index: Dict[str, Dict[str, Dict]] - 文件名小写 -> {文件路径: 文件信息}
    - path_to_key: Dict[str, str] - 文件路径 -> 文件名小写
    这样实现O(1)的查找和更新操作
    """
    
    def __init__(self):
        """初始化索引"""
        self.index = {}
        self.path_to_key = {}
        self.lock = threading.RLock()
        self.last_usn = 0
        self.is_building = False
        self.build_progress = 0
        
    def add_file(self, file_path: str, file_name: str, is_directory: bool = False, 
                 file_size: int = 0, modified_time: float = 0):
        """
        添加文件到索引
        
        Args:
            file_path: 文件完整路径
            file_name: 文件名
            is_directory: 是否为目录
            file_size: 文件大小
            modified_time: 修改时间戳
        """
        with self.lock:
            key = file_name.lower()
            
            file_info = {
                "path": file_path,
                "name": file_name,
                "is_dir": is_directory,
                "size": file_size,
                "mtime": modified_time
            }
            
            old_key = self.path_to_key.get(file_path)
            if old_key is not None and old_key != key:
                if old_key in self.index and file_path in self.index[old_key]:
                    del self.index[old_key][file_path]
                    if not self.index[old_key]:
                        del self.index[old_key]
            
            if key not in self.index:
                self.index[key] = {}
            
            self.index[key][file_path] = file_info
            self.path_to_key[file_path] = key
    
    def batch_add_files(self, files: List[Tuple[str, str, bool, int, float]]):
        """
        批量添加文件到索引（优化性能）
        
        Args:
            files: 文件列表，每个元素为 (file_path, file_name, is_directory, file_size, modified_time)
        """
        with self.lock:
            for file_path, file_name, is_directory, file_size, modified_time in files:
                key = file_name.lower()
                
                file_info = {
                    "path": file_path,
                    "name": file_name,
                    "is_dir": is_directory,
                    "size": file_size,
                    "mtime": modified_time
                }
                
                old_key = self.path_to_key.get(file_path)
                if old_key is not None and old_key != key:
                    if old_key in self.index and file_path in self.index[old_key]:
                        del self.index[old_key][file_path]
                        if not self.index[old_key]:
                            del self.index[old_key]
                
                if key not in self.index:
                    self.index[key] = {}
                
                self.index[key][file_path] = file_info
                self.path_to_key[file_path] = key
    
    def remove_file(self, file_path: str):
        """
        从索引中移除文件
        
        Args:
            file_path: 文件完整路径
        """
        with self.lock:
            key = self.path_to_key.get(file_path)
            if key is None:
                return
            
            if key in self.index and file_path in self.index[key]:
                del self.index[key][file_path]
                if not self.index[key]:
                    del self.index[key]
            
            del self.path_to_key[file_path]
    
    def search(self, keyword: str, max_results: int = 1000, drive_filter: str = None) -> List[Dict]:
        results = []
        keyword_lower = keyword.lower()
        has_wildcard = '*' in keyword_lower or '?' in keyword_lower
        norm_drive = drive_filter[0].lower() if drive_filter and len(drive_filter) >= 1 else None
        
        with self.lock:
            if has_wildcard:
                is_ext_pattern = keyword_lower.startswith('*.') and '?' not in keyword_lower and keyword_lower.count('*') == 1
                if is_ext_pattern:
                    ext = keyword_lower[1:]
                    for key, files_dict in self.index.items():
                        if key.endswith(ext):
                            for file_info in files_dict.values():
                                if norm_drive and not file_info.get('path', '')[:1].lower() == norm_drive:
                                    continue
                                results.append(file_info)
                                if len(results) >= max_results:
                                    break
                        if len(results) >= max_results:
                            break
                else:
                    for key, files_dict in self.index.items():
                        if fnmatch.fnmatch(key, keyword_lower):
                            for file_info in files_dict.values():
                                if norm_drive and not file_info.get('path', '')[:1].lower() == norm_drive:
                                    continue
                                results.append(file_info)
                                if len(results) >= max_results:
                                    break
                        if len(results) >= max_results:
                            break
            else:
                if keyword_lower in self.index:
                    for file_info in self.index[keyword_lower].values():
                        if norm_drive and not file_info.get('path', '')[:1].lower() == norm_drive:
                            continue
                        results.append(file_info)
                
                if len(results) < max_results:
                    for key, files_dict in self.index.items():
                        if keyword_lower in key and key != keyword_lower:
                            for file_info in files_dict.values():
                                if norm_drive and not file_info.get('path', '')[:1].lower() == norm_drive:
                                    continue
                                results.append(file_info)
                                if len(results) >= max_results:
                                    break
                        if len(results) >= max_results:
                            break
            
            return results[:max_results]
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        with self.lock:
            total_files = sum(len(files) for files in self.index.values())
            return {
                "total_entries": len(self.index),
                "total_files": total_files,
                "last_usn": self.last_usn
            }


class WinAPIScanner:
    """
    Windows API文件扫描器
    使用FindFirstFile/FindNextFile实现快速文件枚举
    """
    
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError("WinAPIScanner仅支持Windows平台")
        
        self._setup_windows_api()
    
    def _setup_windows_api(self):
        """设置Windows API"""
        self.kernel32 = ctypes.windll.kernel32
        
        self.FindFirstFileW = self.kernel32.FindFirstFileW
        self.FindFirstFileW.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
        self.FindFirstFileW.restype = wintypes.HANDLE
        
        self.FindNextFileW = self.kernel32.FindNextFileW
        self.FindNextFileW.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        self.FindNextFileW.restype = wintypes.BOOL
        
        self.FindClose = self.kernel32.FindClose
        self.FindClose.argtypes = [wintypes.HANDLE]
        self.FindClose.restype = wintypes.BOOL
        
        self.GetFileAttributesW = self.kernel32.GetFileAttributesW
        self.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        self.GetFileAttributesW.restype = wintypes.DWORD
        
        self.GetVolumeInformationW = self.kernel32.GetVolumeInformationW
        self.GetVolumeInformationW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
            wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD,
            wintypes.LPWSTR, wintypes.DWORD
        ]
        self.GetVolumeInformationW.restype = wintypes.BOOL
        
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
        
        class WIN32_FIND_DATAW(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTime", FILETIME),
                ("ftLastAccessTime", FILETIME),
                ("ftLastWriteTime", FILETIME),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("dwReserved0", wintypes.DWORD),
                ("dwReserved1", wintypes.DWORD),
                ("cFileName", wintypes.WCHAR * 260),
                ("cAlternateFileName", wintypes.WCHAR * 14),
            ]
        
        self.WIN32_FIND_DATAW = WIN32_FIND_DATAW
    
    def _filetime_to_timestamp(self, ft) -> float:
        """将FILETIME转换为Unix时间戳"""
        try:
            filetime = (ft.dwHighDateTime << 32) | ft.dwLowDateTime
            return (filetime - 116444736000000000) / 10000000
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0.0
    
    def _get_file_size(self, data) -> int:
        """从WIN32_FIND_DATA获取文件大小"""
        return (data.nFileSizeHigh << 32) | data.nFileSizeLow
    
    def scan_directory(self, directory: str, callback=None, skip_system_dirs: bool = True) -> int:
        """
        使用Windows API快速扫描目录
        
        Args:
            directory: 目录路径
            callback: 回调函数 (file_path, file_name, is_dir, file_size, mtime)
            skip_system_dirs: 是否跳过系统目录
            
        Returns:
            扫描的文件数量
        """
        processed_count = 0
        stack = [directory]
        dir_count = 0
        
        while stack:
            current_dir = stack.pop()
            
            try:
                find_data = self.WIN32_FIND_DATAW()
                search_path = os.path.join(current_dir, '*')
                
                hFind = self.FindFirstFileW(search_path, ctypes.byref(find_data))
                if hFind == wintypes.HANDLE(-1).value:
                    continue
                
                try:
                    while True:
                        filename = ctypes.wstring_at(find_data.cFileName)
                        
                        if filename in ('.', '..'):
                            if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                break
                            continue
                        
                        is_directory = (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0
                        file_path = os.path.join(current_dir, filename)
                        
                        if is_directory:
                            if skip_system_dirs and filename in SKIP_DIRS:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            if (find_data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            stack.append(file_path)
                            dir_count += 1
                            
                            file_size = 0
                            mtime = self._filetime_to_timestamp(find_data.ftLastWriteTime)
                            
                            if callback:
                                callback(file_path, filename, True, file_size, mtime)
                            
                            processed_count += 1
                        else:
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in SKIP_EXTENSIONS:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            file_size = self._get_file_size(find_data)
                            mtime = self._filetime_to_timestamp(find_data.ftLastWriteTime)
                            
                            if callback:
                                callback(file_path, filename, False, file_size, mtime)
                            
                            processed_count += 1
                        
                        if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                            break
                finally:
                    self.FindClose(hFind)
            except Exception as e:
                logger.debug(f"操作跳过: {e}")
                continue
        return processed_count
    
    def scan_directory_recursive(self, directory: str, result_queue, stop_event):
        """
        递归扫描目录（用于多线程）
        
        Args:
            directory: 目录路径
            result_queue: 结果队列
            stop_event: 停止事件
        """
        stack = [directory]
        
        while stack and not stop_event.is_set():
            current_dir = stack.pop()
            
            try:
                find_data = self.WIN32_FIND_DATAW()
                search_path = os.path.join(current_dir, '*')
                
                hFind = self.FindFirstFileW(search_path, ctypes.byref(find_data))
                if hFind == wintypes.HANDLE(-1).value:
                    continue
                
                try:
                    batch = []
                    while True:
                        filename = ctypes.wstring_at(find_data.cFileName)
                        
                        if filename in ('.', '..'):
                            if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                break
                            continue
                        
                        is_directory = (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0
                        file_path = os.path.join(current_dir, filename)
                        
                        if is_directory:
                            if filename in SKIP_DIRS:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            if (find_data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            stack.append(file_path)
                            
                            file_size = 0
                            mtime = self._filetime_to_timestamp(find_data.ftLastWriteTime)
                            
                            batch.append((file_path, filename, True, file_size, mtime))
                            
                            if len(batch) >= 1000:
                                result_queue.put(batch)
                                batch = []
                        else:
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in SKIP_EXTENSIONS:
                                if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                                    break
                                continue
                            
                            file_size = self._get_file_size(find_data)
                            mtime = self._filetime_to_timestamp(find_data.ftLastWriteTime)
                            
                            batch.append((file_path, filename, False, file_size, mtime))
                            
                            if len(batch) >= 1000:
                                result_queue.put(batch)
                                batch = []
                        
                        if not self.FindNextFileW(hFind, ctypes.byref(find_data)):
                            break
                    
                    if batch:
                        result_queue.put(batch)
                finally:
                    self.FindClose(hFind)
            except Exception as e:
                logger.debug(f"操作跳过: {e}")
                continue
    def get_drive_file_system(self, drive_letter: str) -> str:
        """获取驱动器文件系统类型"""
        fs_type = ctypes.create_unicode_buffer(64)
        try:
            self.GetVolumeInformationW(
                f"{drive_letter}:\\", None, 0, None, None, None,
                fs_type, len(fs_type)
            )
            return fs_type.value.upper()
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return ""
    
    def scan_mft(self, drive_letter: str, result_queue, stop_event):
        """
        使用MFT直接枚举扫描整个NTFS卷（增量更新专用）
        通过FSCTL_ENUM_USN_DATA获取文件变更记录
        
        注意：此方法主要用于增量更新，因为MFT记录只包含父文件引用号(FRN)，
        需要额外的路径解析步骤才能获得完整路径。对于首次索引，使用scan_directory_recursive更可靠。
        
        Args:
            drive_letter: 驱动器字母（如 'C'）
            result_queue: 结果队列
            stop_event: 停止事件
        """
        import struct
        
        volume_path = f"\\\\.\\{drive_letter}:"
        processed = 0
        
        try:
            hVolume = ctypes.windll.kernel32.CreateFileW(
                volume_path,
                wintypes.DWORD(0x80000000),  # GENERIC_READ only
                wintypes.DWORD(FILE_SHARE_READ | FILE_SHARE_WRITE),
                None,
                wintypes.DWORD(OPEN_EXISTING),
                wintypes.DWORD(0),
                None
            )
            
            if hVolume == wintypes.HANDLE(-1).value:
                logger.debug(f"[MFT] 无法打开卷 {drive_letter}: (可能需要管理员权限)")
                return processed
            
            try:
                mft_data = self._get_mft_enum_data(hVolume)
                if mft_data is None:
                    logger.debug(f"[MFT] {drive_letter}: 无法获取MFT枚举数据")
                    return processed
                
                buffer_size = 2 * 1024 * 1024  # 2MB buffer
                buffer = ctypes.create_string_buffer(buffer_size)
                
                batch = []
                
                while not stop_event.is_set():
                    bytes_returned = wintypes.DWORD(0)
                    success = ctypes.windll.kernel32.DeviceIoControl(
                        hVolume,
                        wintypes.DWORD(FSCTL_ENUM_USN_DATA),
                        ctypes.byref(mft_data),
                        ctypes.sizeof(mft_data),
                        buffer,
                        buffer_size,
                        ctypes.byref(bytes_returned),
                        None
                    )
                    
                    if not success or bytes_returned.value <= 8:
                        break
                    
                    offset = 8
                    while offset < bytes_returned.value:
                        if offset + 16 > bytes_returned.value:
                            break
                        
                        record_length = struct.unpack_from('<I', buffer, offset)[0]
                        major_version = struct.unpack_from('<H', buffer, offset + 4)[0]
                        
                        if record_length == 0 or offset + record_length > bytes_returned.value:
                            break
                        
                        try:
                            if major_version >= 2:
                                file_reference_number = struct.unpack_from('<Q', buffer, offset + 8)[0]
                                parent_file_reference_number = struct.unpack_from('<Q', buffer, offset + 16)[0]
                                file_attributes = struct.unpack_from('<I', buffer, offset + 44)[0]
                                filename_offset = struct.unpack_from('<H', buffer, offset + 48)[0]
                                filename_length = struct.unpack_from('<H', buffer, offset + 50)[0]
                                
                                filename_start = offset + filename_offset
                                filename_bytes = buffer[filename_start:filename_start + filename_length]
                                filename = filename_bytes.decode('utf-16-le', errors='ignore')
                                
                                is_directory = (file_attributes & FILE_ATTRIBUTE_DIRECTORY) != 0
                                is_hidden = (file_attributes & FILE_ATTRIBUTE_HIDDEN) != 0
                                is_system = (file_attributes & FILE_ATTRIBUTE_SYSTEM) != 0
                                is_reparse = (file_attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0
                                
                                if is_directory:
                                    if filename in SKIP_DIRS or is_hidden or is_system:
                                        offset += record_length
                                        continue
                                    if is_reparse:
                                        offset += record_length
                                        continue
                                else:
                                    ext = os.path.splitext(filename)[1].lower()
                                    if ext in SKIP_EXTENSIONS or is_hidden or is_system:
                                        offset += record_length
                                        continue
                                
                                # 注意：MFT扫描无法直接获取完整路径（需要FRN→路径映射表），
                                # 此处路径仅包含盘符根目录，不是文件的实际完整路径。
                                # 搜索结果中通过 _mft_incomplete_path 标记提示用户路径不完整。
                                file_path = f"{drive_letter}:\\"
                                batch.append((file_path, filename, is_directory, 0, 0, True))
                                
                                processed += 1
                                
                                if len(batch) >= 5000:
                                    result_queue.put(batch)
                                    batch = []
                            
                        except Exception as e:
                            logger.debug(f"操作失败: {e}")
                        offset += record_length
                    
                    mft_data.StartFileReferenceNumber = struct.unpack_from('<Q', buffer, 0)[0]
                
                if batch:
                    result_queue.put(batch)
                
                logger.info(f"[MFT] {drive_letter}: 扫描完成，处理 {processed} 个文件")
                
            finally:
                ctypes.windll.kernel32.CloseHandle(hVolume)
                
        except Exception as e:
            logger.error(f"[MFT] {drive_letter}: 扫描失败: {e}")
        
        return processed
    
    def _get_mft_enum_data(self, hVolume):
        """获取MFT枚举数据结构"""
        import struct
        
        try:
            class MFT_ENUM_DATA_V0(ctypes.Structure):
                _fields_ = [
                    ("StartFileReferenceNumber", wintypes.LONGLONG),
                    ("LowUsn", wintypes.LONGLONG),
                    ("HighUsn", wintypes.LONGLONG),
                ]
            
            mft_data = MFT_ENUM_DATA_V0()
            mft_data.StartFileReferenceNumber = 0
            mft_data.LowUsn = 0
            mft_data.HighUsn = 0xFFFFFFFFFFFFFFFF
            
            return mft_data
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return None


class FastSearchService:
    """
    快速搜索服务
    整合NTFS索引和传统搜索，提供统一的搜索接口
    """
    
    def __init__(self):
        """初始化搜索服务"""
        self.ntfs_index = NTFSSearchIndex()
        self.win_api_scanner = None
        if sys.platform == 'win32':
            try:
                self.win_api_scanner = WinAPIScanner()
            except Exception as e:
                logger.warning(f"初始化WinAPIScanner失败: {e}")
        
        self.index_built = False
        self.build_thread = None
        self.build_event = threading.Event()
        
        self._check_index_status()
        
        logger.info("快速搜索服务已初始化")
    
    def _check_index_status(self) -> None:
        """检查索引状态（验证实际索引文件是否存在）"""
        try:
            config_path = Path("config/index_status.json")
            db_path = Path("config/index_data.db")
            
            if config_path.exists():
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config_index_built = data.get('index_built', False)
                    
                    if config_index_built:
                        if db_path.exists():
                            self.index_built = True
                            indexed_drives = data.get('indexed_drives', [])
                            last_build_time = data.get('last_build_time', '')
                            logger.info(f"检测到已有索引: {indexed_drives}, 构建时间: {last_build_time}")
                        else:
                            self.index_built = False
                            logger.warning(f"配置文件存在但数据库文件不存在，需要重新构建索引")
                            self._cleanup_corrupt_index()
            else:
                self.index_built = False
                logger.info(f"配置文件不存在，索引未构建")
        except Exception as e:
            logger.error(f"检查索引状态失败: {e}")
            self.index_built = False
    
    def _cleanup_corrupt_index(self) -> None:
        """清理损坏的索引配置"""
        try:
            config_path = Path("config/index_status.json")
            if config_path.exists():
                config_path.unlink()
                logger.info("已清理损坏的索引配置文件")
        except Exception as e:
            logger.error(f"清理损坏索引配置失败: {e}")
    
    def _save_index_status(self, indexed_drives: List[str] = None) -> None:
        """保存索引状态到配置文件"""
        try:
            import json
            
            config_path = Path("config/index_status.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'index_built': self.index_built,
                'indexed_drives': indexed_drives or [],
                'last_build_time': datetime.now().isoformat(),
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引状态失败: {e}")
    
    def _save_index_data(self, indexed_drives: List[str]) -> None:
        """保存索引数据到SQLite（优化版持久化）"""
        conn = None
        try:
            import sqlite3
            
            db_path = Path("config/index_data.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_path TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_key TEXT NOT NULL,
                    is_directory INTEGER NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_time REAL NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_key ON files(file_key)
            ''')
            
            cursor.execute('DELETE FROM files')
            
            with self.ntfs_index.lock:
                for key, files_dict in self.ntfs_index.index.items():
                    rows = []
                    for file_path, file_info in files_dict.items():
                        rows.append((
                            file_path,
                            file_info['name'],
                            key,
                            1 if file_info['is_dir'] else 0,
                            file_info['size'],
                            file_info['mtime']
                        ))
                        if len(rows) >= 10000:
                            cursor.executemany('''
                                INSERT OR REPLACE INTO files 
                                (file_path, file_name, file_key, is_directory, file_size, modified_time)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', rows)
                            rows = []
                    if rows:
                        cursor.executemany('''
                            INSERT OR REPLACE INTO files 
                            (file_path, file_name, file_key, is_directory, file_size, modified_time)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', rows)
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            cursor.execute('DELETE FROM metadata')
            cursor.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', ('last_usn', str(self.ntfs_index.last_usn)))
            cursor.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', ('indexed_drives', ','.join(indexed_drives)))
            cursor.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', ('saved_time', datetime.now().isoformat()))
            
            conn.commit()
            
            logger.info("索引数据已保存到SQLite")
        except Exception as e:
            logger.error(f"保存索引数据失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def _load_index_data(self) -> bool:
        """从SQLite加载索引数据（优化版）"""
        conn = None
        try:
            import sqlite3
            
            db_path = Path("config/index_data.db")
            if not db_path.exists():
                return False
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT file_path, file_name, file_key, is_directory, file_size, modified_time FROM files')
            
            batch = []
            row_count = 0
            
            with self.ntfs_index.lock:
                self.ntfs_index.index = {}
                self.ntfs_index.path_to_key = {}
                
                for row in cursor.fetchall():
                    file_path, file_name, file_key, is_directory, file_size, modified_time = row
                    
                    file_info = {
                        "path": file_path,
                        "name": file_name,
                        "is_dir": bool(is_directory),
                        "size": file_size,
                        "mtime": modified_time
                    }
                    
                    if file_key not in self.ntfs_index.index:
                        self.ntfs_index.index[file_key] = {}
                    
                    self.ntfs_index.index[file_key][file_path] = file_info
                    self.ntfs_index.path_to_key[file_path] = file_key
                    
                    row_count += 1
            
            cursor.execute('SELECT value FROM metadata WHERE key = ?', ('last_usn',))
            result = cursor.fetchone()
            if result:
                self.ntfs_index.last_usn = int(result[0])
            
            cursor.execute('SELECT value FROM metadata WHERE key = ?', ('indexed_drives',))
            result = cursor.fetchone()
            indexed_drives = result[0].split(',') if result else []
            
            cursor.execute('SELECT value FROM metadata WHERE key = ?', ('saved_time',))
            result = cursor.fetchone()
            saved_time = result[0] if result else ''
            
            logger.info(f"已从SQLite加载索引: {row_count}个文件, {len(indexed_drives)}个盘符, 保存时间: {saved_time}")
            return True
        except Exception as e:
            logger.error(f"加载索引数据失败: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def build_index_async(self, drives: List[str] = None, callback=None):
        """
        异步构建索引
        
        Args:
            drives: 要索引的盘符列表，默认所有NTFS盘
            callback: 进度回调函数
        """
        if self.build_thread and self.build_thread.is_alive():
            logger.warning("索引正在构建中")
            return
        
        if drives is None:
            drives = self._detect_ntfs_drives()
        
        self.build_thread = threading.Thread(
            target=self._build_index,
            args=(drives, callback),
            daemon=True
        )
        self.build_thread.start()
    
    def _build_index(self, drives: List[str], callback=None):
        """
        构建索引（内部方法）
        
        Args:
            drives: 盘符列表
            callback: 进度回调
        """
        self.ntfs_index.is_building = True
        start_time = time.time()
        
        logger.info(f"[FastSearch] 开始构建NTFS文件名索引，盘符: {drives}")
        logger.info(f"[FastSearch] 开始构建索引，盘符: {drives}")
        
        total_files_processed = 0
        stop_event = threading.Event()
        
        try:
            if self.win_api_scanner:
                total_files_processed = self._build_index_with_winapi(drives, callback, stop_event)
            else:
                total_files_processed = self._build_index_with_oswalk(drives, callback, stop_event)
            
            self._save_index_data(drives)
            
        except Exception as e:
            logger.error(f"[FastSearch] 索引构建失败: {e}", exc_info=True)
            logger.error(f"[FastSearch] 索引构建失败: {e}")
            self.index_built = False
            self.ntfs_index.is_building = False
            self.build_event.set()
            return
        
        self.index_built = True
        self.ntfs_index.is_building = False
        
        self._save_index_status(drives)
        self.build_event.set()
        
        elapsed = time.time() - start_time
        stats = self.ntfs_index.get_stats()
        
        logger.info(f"[FastSearch] NTFS文件名索引构建完成! 耗时: {elapsed:.2f}秒, 总文件数: {stats['total_files']}, 索引条目: {stats['total_entries']}")
        logger.info(f"[FastSearch] 索引构建完成! 耗时: {elapsed:.2f}秒, 总文件数: {stats['total_files']}, 索引条目: {stats['total_entries']}")
    
    def _build_index_with_winapi(self, drives: List[str], callback=None, stop_event=None):
        """
        使用Windows API构建索引（并行扫描优化版）
        
        优化点：
        1. 并行扫描多个驱动器
        2. 使用scan_directory_recursive（可靠的完整路径扫描）
        3. 批量添加索引，减少锁竞争
        4. 独立的消费者线程处理结果
        5. 线程安全计数器
        6. MFT扫描作为增量更新备选
        
        Args:
            drives: 盘符列表
            callback: 进度回调
            stop_event: 停止事件
            
        Returns:
            处理的文件总数
        """
        import queue
        
        total_files = 0
        total_files_lock = threading.Lock()
        drive_stats = {drive: {'processed': 0, 'total': 0} for drive in drives}
        scan_threads = []
        consumer_threads = []
        
        stop_event = stop_event or threading.Event()
        
        def process_results(drive, result_queue, consumer_stop_event):
            nonlocal total_files
            last_callback_time = time.time()
            last_logged_percent = -1
            
            while not consumer_stop_event.is_set():
                try:
                    batch = result_queue.get(timeout=0.5)
                    if batch is None:
                        break
                    
                    self.ntfs_index.batch_add_files(batch)
                    
                    with total_files_lock:
                        drive_stats[drive]['processed'] += len(batch)
                        total_files += len(batch)
                    
                    current_time = time.time()
                    if callback and (current_time - last_callback_time) >= 0.5:
                        processed = drive_stats[drive]['processed']
                        if drive_stats[drive]['total'] > 0:
                            estimated_total = drive_stats[drive]['total']
                        else:
                            estimated_total = max(processed * 3, 100000)
                        progress = min((processed / estimated_total) * 95, 95)
                        
                        current_percent = int(progress / 5) * 5
                        if current_percent > last_logged_percent and current_percent > 0:
                            logger.info(f"[FastSearch] {drive} 索引进度: {current_percent}% ({processed} 文件)")
                            last_logged_percent = current_percent
                        
                        callback(drive, progress, processed, estimated_total)
                        last_callback_time = current_time
                except queue.Empty:
                    continue
        
        # 为每个驱动器创建扫描线程和消费者线程
        for drive in drives:
            drive_path = f"{drive}:\\"
            if not os.path.exists(drive_path):
                continue
            
            result_queue = queue.Queue(maxsize=50)
            consumer_stop_event = threading.Event()
            
            # 创建扫描线程（使用scan_directory_recursive获取完整路径）
            scan_thread = threading.Thread(
                target=self.win_api_scanner.scan_directory_recursive,
                args=(drive_path, result_queue, stop_event),
                daemon=True,
                name=f"Scan-{drive}"
            )
            scan_threads.append((drive, scan_thread, result_queue))
            
            # 创建消费者线程
            consumer_thread = threading.Thread(
                target=process_results,
                args=(drive, result_queue, consumer_stop_event),
                daemon=True,
                name=f"Consumer-{drive}"
            )
            consumer_threads.append((consumer_thread, consumer_stop_event))
            consumer_thread.start()
            
            scan_thread.start()
        
        # 等待所有扫描线程完成并发送结束信号
        for drive, scan_thread, result_queue in scan_threads:
            scan_thread.join(timeout=120)
            result_queue.put(None)
        
        # 等待所有消费者线程完成
        for consumer_thread, consumer_stop_event in consumer_threads:
            consumer_stop_event.set()
            consumer_thread.join(timeout=30)
        
        for drive in drives:
            drive_path = f"{drive}:\\"
            if not os.path.exists(drive_path):
                continue
            logger.info(f"[FastSearch] {drive} 索引完成，共 {drive_stats[drive]['processed']} 个文件")
            logger.info(f"[FastSearch] {drive} 索引完成，共 {drive_stats[drive]['processed']} 个文件")
            if callback:
                callback(drive, 100, drive_stats[drive]['processed'], drive_stats[drive]['processed'])
        
        return total_files
    
    def _build_index_with_oswalk(self, drives: List[str], callback=None, stop_event=None):
        """
        使用os.scandir构建索引（优化版备选方案）
        
        优化点：
        1. 使用os.scandir替代os.walk，避免大量os.stat()调用
        2. 批量添加索引，减少锁竞争
        3. 递归扫描使用栈代替递归调用
        
        Args:
            drives: 盘符列表
            callback: 进度回调
            stop_event: 停止事件
            
        Returns:
            处理的文件总数
        """
        total_files = 0
        
        for drive in drives:
            drive_path = f"{drive}:\\"
            if not os.path.exists(drive_path):
                continue
            
            drive_file_count = 0
            last_callback_time = time.time()
            batch = []
            
            try:
                stack = [drive_path]
                
                while stack and (not stop_event or not stop_event.is_set()):
                    current_dir = stack.pop()
                    
                    try:
                        with os.scandir(current_dir) as entries:
                            for entry in entries:
                                try:
                                    if entry.is_symlink():
                                        continue
                                    
                                    if entry.is_dir(follow_symlinks=False):
                                        if entry.name in SKIP_DIRS:
                                            continue
                                        
                                        if entry.is_symlink():
                                            continue
                                        
                                        stack.append(entry.path)
                                        
                                        mtime = entry.stat(follow_symlinks=False).st_mtime
                                        batch.append((entry.path, entry.name, True, 0, mtime))
                                    else:
                                        ext = os.path.splitext(entry.name)[1].lower()
                                        if ext in SKIP_EXTENSIONS:
                                            continue
                                        
                                        stat_info = entry.stat(follow_symlinks=False)
                                        batch.append((entry.path, entry.name, False, stat_info.st_size, stat_info.st_mtime))
                                        
                                    drive_file_count += 1
                                    total_files += 1
                                    
                                    if len(batch) >= 2000:
                                        self.ntfs_index.batch_add_files(batch)
                                        batch = []
                                        
                                        current_time = time.time()
                                        if callback and (current_time - last_callback_time) >= 1.0:
                                            estimated_total = drive_file_count * 8
                                            progress = min((drive_file_count / estimated_total) * 100, 95)
                                            callback(drive, progress, drive_file_count, estimated_total)
                                            last_callback_time = current_time
                                
                                except (OSError, PermissionError):
                                    continue
                    except (OSError, PermissionError):
                        continue
                
                if batch:
                    self.ntfs_index.batch_add_files(batch)
                
                logger.info(f"[FastSearch] {drive} 索引完成，共 {drive_file_count} 个文件")
                logger.info(f"[FastSearch] {drive} 索引完成，共 {drive_file_count} 个文件")
                
            except Exception as e:
                logger.error(f"[FastSearch] {drive} 索引失败: {e}", exc_info=True)
                logger.error(f"[FastSearch] {drive} 索引失败: {e}")
        
        return total_files
    
    def search(self, keyword: str, max_results: int = 1000, directory: str = None) -> List[Dict]:
        if not self.index_built:
            logger.warning("索引尚未构建，使用传统搜索")
            return self._traditional_search(keyword, max_results)
        
        start_time = time.time()
        results = self.ntfs_index.search(keyword, max_results, drive_filter=directory)
        elapsed = time.time() - start_time
        
        logger.debug(f"搜索 '{keyword}' 找到 {len(results)} 个结果，耗时 {elapsed*1000:.2f}ms")
        
        return results
    
    def _traditional_search(self, keyword: str, max_results: int = 1000, callback=None, stop_event=None) -> List[Dict]:
        """
        传统搜索方法（备选）
        
        Args:
            keyword: 搜索关键字
            max_results: 最大结果数
            callback: 进度回调函数，签名 callback(processed_count)
            stop_event: 停止事件，设置后提前退出
            
        Returns:
            搜索结果列表
        """
        results = []
        keyword_lower = keyword.lower()
        processed_count = 0
        
        search_paths = [os.path.expanduser("~")]
        
        if sys.platform == 'win32':
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    search_paths.append(drive)
        
        for search_path in search_paths:
            if len(results) >= max_results:
                break
            
            if stop_event and stop_event.is_set():
                break
            
            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    
                    if stop_event and stop_event.is_set():
                        break
                    
                    for filename in files:
                        processed_count += 1
                        
                        if stop_event and stop_event.is_set():
                            break
                        
                        if callback and processed_count % 1000 == 0:
                            callback(processed_count)
                        
                        if keyword_lower in filename.lower():
                            filepath = os.path.join(root, filename)
                            try:
                                stat = os.stat(filepath)
                                results.append({
                                    "path": filepath,
                                    "name": filename,
                                    "is_dir": False,
                                    "size": stat.st_size,
                                    "mtime": stat.st_mtime
                                })
                                
                                if len(results) >= max_results:
                                    return results
                            except (PermissionError, OSError):
                                continue
            except (PermissionError, OSError):
                continue
        
        return results
    
    def _detect_ntfs_drives(self) -> List[str]:
        """检测所有NTFS格式的驱动器"""
        ntfs_drives = []
        
        if sys.platform == 'win32':
            import string
            
            if self.win_api_scanner:
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        try:
                            fs_type = self.win_api_scanner.get_drive_file_system(letter)
                            if fs_type == "NTFS":
                                ntfs_drives.append(letter)
                        except Exception as e:
                            logger.debug(f"操作跳过: {e}")
                            continue
            else:
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        try:
                            fs_type = ctypes.create_unicode_buffer(64)
                            ctypes.windll.kernel32.GetVolumeInformationW(
                                drive, None, 0, None, None, None,
                                fs_type, len(fs_type)
                            )
                            if fs_type.value.upper() == "NTFS":
                                ntfs_drives.append(letter)
                        except Exception as e:
                            logger.debug(f"操作失败: {e}")
        
        return ntfs_drives
    
    def update_index_from_usn(self):
        """从USN Journal更新索引（增量更新）"""
        if sys.platform != 'win32':
            logger.info("[FastSearch] USN Journal仅支持Windows平台")
            return
        
        logger.info("[FastSearch] 开始USN Journal增量更新")
        
        try:
            for drive_letter in self._detect_ntfs_drives():
                changes = self._read_usn_journal(drive_letter)
                
                for change in changes:
                    filename = change.get('filename', '')
                    reason = change.get('reason', 0)
                    
                    USN_REASON_FILE_DELETE = 0x00000200
                    USN_REASON_FILE_CREATE = 0x00000100
                    
                    if reason & USN_REASON_FILE_DELETE:
                        results = self.ntfs_index.search(filename, max_results=100)
                        for result in results:
                            if result['name'] == filename:
                                self.ntfs_index.remove_file(result['path'])
                    
                    elif reason & USN_REASON_FILE_CREATE:
                        file_ref = change.get('file_reference_number')
                        parent_ref = change.get('parent_directory_file_reference_number')
                        if file_ref and parent_ref:
                            try:
                                filepath = self._resolve_file_path(drive_letter, file_ref, parent_ref, filename)
                                if filepath and os.path.exists(filepath):
                                    try:
                                        stat = os.stat(filepath)
                                        self.ntfs_index.add_file(
                                            filepath, filename,
                                            is_directory=False,
                                            file_size=stat.st_size,
                                            modified_time=stat.st_mtime
                                        )
                                    except (PermissionError, OSError):
                                        pass
                            except Exception as e:
                                logger.debug(f"[FastSearch] USN CREATE处理失败: {filename}, 错误: {e}")
            
            logger.info("[FastSearch] USN增量更新完成")
        except Exception as e:
            logger.error(f"[FastSearch] USN更新失败: {e}")
    
    def _resolve_file_path(self, drive_letter: str, file_ref: int, parent_ref: int, filename: str) -> str:
        try:
            import ctypes
            parent_path = f"{drive_letter}:\\"
            
            volume_path = f"\\\\.\\{drive_letter}:"
            hVolume = ctypes.windll.kernel32.CreateFileW(
                volume_path,
                0x80000000,
                0x00000001 | 0x00000002,
                None,
                3,
                0x02000000,
                None
            )
            
            if hVolume == -1:
                return os.path.join(parent_path, filename)
            
            try:
                class FILE_ID_DESCRIPTOR(ctypes.Structure):
                    _fields_ = [
                        ("dwSize", ctypes.c_ulong),
                        ("Type", ctypes.c_ulong),
                        ("FileId", ctypes.c_ulonglong),
                    ]
                
                fid = FILE_ID_DESCRIPTOR()
                fid.dwSize = ctypes.sizeof(FILE_ID_DESCRIPTOR)
                fid.Type = 0
                fid.FileId = parent_ref
                
                hFile = ctypes.windll.kernel32.OpenFileById(
                    hVolume,
                    ctypes.byref(fid),
                    0x80000000,
                    0x00000001 | 0x00000002,
                    None,
                    0x02000000
                )
                
                if hFile != -1:
                    try:
                        buf = ctypes.create_unicode_buffer(4096)
                        if ctypes.windll.kernel32.GetFinalPathNameByHandleW(hFile, buf, 4096, 0) > 0:
                            parent_path = buf.value
                            if parent_path.startswith('\\\\?\\'):
                                parent_path = parent_path[4:]
                    finally:
                        ctypes.windll.kernel32.CloseHandle(hFile)
            finally:
                ctypes.windll.kernel32.CloseHandle(hVolume)
            
            return os.path.join(parent_path, filename)
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return os.path.join(f"{drive_letter}:\\", filename)
    
    def _read_usn_journal(self, drive_letter: str) -> List[Dict]:
        """读取USN Journal"""
        changes = []
        
        try:
            import win32file
            import win32con
            import winioctlcon
            
            volume_handle = win32file.CreateFile(
                f"\\\\.\\{drive_letter}:",
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            
            try:
                journal_data = win32file.DeviceIoControl(
                    volume_handle,
                    winioctlcon.FSCTL_QUERY_USN_JOURNAL,
                    None,
                    1024
                )
                
                if len(journal_data) >= 24:
                    journal_id = struct.unpack_from('<Q', journal_data, 0)[0]
                    first_usn = struct.unpack_from('<q', journal_data, 8)[0]
                    next_usn = struct.unpack_from('<q', journal_data, 16)[0]
                    
                    if next_usn > first_usn:
                        read_data = struct.pack('<QQQ', journal_id, first_usn, next_usn)
                        
                        usn_data = win32file.DeviceIoControl(
                            volume_handle,
                            winioctlcon.FSCTL_READ_USN_JOURNAL,
                            read_data,
                            65536
                        )
                        
                        offset = 8
                        while offset < len(usn_data):
                            if offset + 4 > len(usn_data):
                                break
                            
                            record_length = struct.unpack_from('<I', usn_data, offset)[0]
                            if record_length == 0 or offset + record_length > len(usn_data):
                                break
                            
                            try:
                                record_version = struct.unpack_from('<H', usn_data, offset + 4)[0]
                                if record_version == 2:
                                    filename_offset = struct.unpack_from('<H', usn_data, offset + 58)[0]
                                    filename_length = struct.unpack_from('<H', usn_data, offset + 60)[0]
                                    
                                    filename_start = offset + filename_offset
                                    filename_bytes = usn_data[filename_start:filename_start + filename_length]
                                    filename = filename_bytes.decode('utf-16-le', errors='ignore')
                                    
                                    reason = struct.unpack_from('<I', usn_data, offset + 20)[0]
                                    
                                    changes.append({
                                        'filename': filename,
                                        'reason': reason,
                                        'usn': struct.unpack_from('<q', usn_data, offset + 8)[0]
                                    })
                            except Exception as e:
                                logger.debug(f"操作失败: {e}")
                            offset += record_length
                
                logger.info(f"[NTFS] 读取USN Journal成功，变更记录数: {len(changes)}")
                
            finally:
                win32file.CloseHandle(volume_handle)
                
        except ImportError:
            logger.warning("[NTFS] pywin32未安装，无法读取USN Journal")
        except Exception as e:
            logger.error(f"[NTFS] 读取USN Journal失败: {e}")
        
        return changes
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        return self.ntfs_index.get_stats()


# 全局实例
fast_search_service = FastSearchService()