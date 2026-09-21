import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
import sys

from core.logger import logger as _logger


class IndexLocationManager:
    MIN_FREE_SPACE = 1024 * 1024 * 1024
    
    def __init__(self):
        self._logger = _logger
    
    def get_default_location(self) -> str:
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return str(Path(appdata) / 'AFM-EST' / 'index')
        elif sys.platform == 'darwin':
            return str(Path.home() / 'Library' / 'Application Support' / 'AFM-EST' / 'index')
        else:
            return str(Path.home() / '.local' / 'share' / 'AFM-EST' / 'index')
    
    def validate_location(self, location: str) -> Tuple[bool, str]:
        path = Path(location)
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False, f"无权限创建目录: {location}"
        except Exception as e:
            _logger.debug(f"创建目录失败: {e}")
            return False, f"创建目录失败: {e}"
        
        if not os.access(path.parent, os.W_OK):
            return False, f"无写入权限: {location}"
        
        free_space = self.get_free_space(str(path.parent))
        if free_space < self.MIN_FREE_SPACE:
            return False, f"磁盘空间不足（需要至少1GB）: {location}"
        
        return True, "验证通过"
    
    def get_free_space(self, path: str) -> int:
        try:
            if sys.platform == 'win32':
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path),
                    None,
                    None,
                    ctypes.pointer(free_bytes)
                )
                return free_bytes.value
            else:
                stat = os.statvfs(path)
                return stat.f_bavail * stat.f_frsize
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0
    
    def ensure_location_exists(self, location: str) -> bool:
        path = Path(location)
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self._logger.error(f"Failed to create index location: {e}")
            return False
    
    def migrate_index(self, source: str, target: str, progress_callback=None) -> Tuple[bool, str]:
        source_path = Path(source)
        target_path = Path(target)
        
        if not source_path.exists():
            return False, f"源索引目录不存在: {source}"
        
        valid, msg = self.validate_location(target)
        if not valid:
            return False, msg
        
        try:
            target_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            _logger.debug(f"创建目标目录失败: {e}")
            return False, f"创建目标目录失败: {e}"
        
        try:
            total_size = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file())
            copied_size = 0
            
            for item in source_path.iterdir():
                if item.is_file():
                    target_file = target_path / item.name
                    shutil.copy2(item, target_file)
                    copied_size += item.stat().st_size
                    
                    if progress_callback:
                        progress = (copied_size / total_size) * 100 if total_size > 0 else 100
                        progress_callback(progress)
                
                elif item.is_dir():
                    target_dir = target_path / item.name
                    shutil.copytree(item, target_dir)
                    dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    copied_size += dir_size
                    
                    if progress_callback:
                        progress = (copied_size / total_size) * 100 if total_size > 0 else 100
                        progress_callback(progress)
            
            return True, "迁移成功"
        
        except Exception as e:
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            return False, f"迁移失败: {e}"
    
    def get_index_size(self, location: str) -> int:
        path = Path(location)
        
        if not path.exists():
            return 0
        
        try:
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0
    
    def clear_index(self, location: str) -> Tuple[bool, str]:
        path = Path(location)
        
        if not path.exists():
            return True, "索引目录不存在"
        
        try:
            shutil.rmtree(path)
            return True, "索引已清除"
        except Exception as e:
            _logger.debug(f"清除索引失败: {e}")
            return False, f"清除索引失败: {e}"