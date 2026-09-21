from pathlib import Path
from typing import Optional, Union
import os
import locale

from core.logger import logger
from .platform_detector import platform_detector


class FileSystemAdapter:
    def __init__(self):
        self._detector = platform_detector
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        return Path(path).resolve()
    
    def join_path(self, *parts: Union[str, Path]) -> Path:
        return Path(*parts)
    
    def is_absolute_path(self, path: Union[str, Path]) -> bool:
        return Path(path).is_absolute()
    
    def get_parent_path(self, path: Union[str, Path]) -> Path:
        return Path(path).parent
    
    def get_file_name(self, path: Union[str, Path]) -> str:
        return Path(path).name
    
    def get_file_extension(self, path: Union[str, Path]) -> str:
        return Path(path).suffix
    
    def get_file_stem(self, path: Union[str, Path]) -> str:
        return Path(path).stem
    
    def convert_to_platform_path(self, path: Union[str, Path]) -> Path:
        path_str = str(path)
        
        if self._detector.is_windows():
            if path_str.startswith('/mnt/'):
                parts = path_str[5:].split('/', 1)
                if len(parts) >= 1 and len(parts[0]) == 1:
                    drive = parts[0].upper()
                    rest = parts[1] if len(parts) > 1 else ''
                    return Path(f"{drive}:\\{rest.replace('/', '\\')}")
        
        else:
            if len(path_str) >= 2 and path_str[1] == ':':
                drive = path_str[0].lower()
                rest = path_str[2:].replace('\\', '/')
                return Path(f"/mnt/{drive}{rest}")
        
        return Path(path)
    
    def get_user_directory(self, dir_type: str = 'home') -> Optional[Path]:
        if dir_type == 'home':
            return Path.home()
        
        if self._detector.is_windows():
            if dir_type == 'documents':
                docs = os.environ.get('USERPROFILE', '')
                if docs:
                    return Path(docs) / 'Documents'
            elif dir_type == 'downloads':
                profile = os.environ.get('USERPROFILE', '')
                if profile:
                    return Path(profile) / 'Downloads'
            elif dir_type == 'desktop':
                profile = os.environ.get('USERPROFILE', '')
                if profile:
                    return Path(profile) / 'Desktop'
        
        else:
            home = Path.home()
            xdg_config = os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))
            
            user_dirs_file = Path(xdg_config) / 'user-dirs.dirs'
            if user_dirs_file.exists():
                try:
                    with open(user_dirs_file, 'r') as f:
                        for line in f:
                            if line.startswith(f'XDG_{dir_type.upper()}_DIR'):
                                path_str = line.split('=')[1].strip().strip('"')
                                if path_str.startswith('$HOME'):
                                    path_str = str(home) + path_str[5:]
                                return Path(path_str)
                except Exception as e:
                    logger.debug(f"读取用户目录配置失败: {e}")
            
            loc = locale.getlocale()[0] or ''
            if dir_type == 'documents':
                if loc.startswith('zh'):
                    return home / '文档'
                return home / 'Documents'
            elif dir_type == 'downloads':
                if loc.startswith('zh'):
                    return home / '下载'
                return home / 'Downloads'
            elif dir_type == 'desktop':
                if loc.startswith('zh'):
                    return home / '桌面'
                return home / 'Desktop'
            elif dir_type == 'music':
                if loc.startswith('zh'):
                    return home / '音乐'
                return home / 'Music'
            elif dir_type == 'pictures':
                if loc.startswith('zh'):
                    return home / '图片'
                return home / 'Pictures'
            elif dir_type == 'videos':
                if loc.startswith('zh'):
                    return home / '视频'
                return home / 'Videos'
        
        return None
    
    def ensure_directory(self, path: Union[str, Path]) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p
    
    def is_hidden_file(self, path: Union[str, Path]) -> bool:
        p = Path(path)
        name = p.name
        
        if self._detector.is_windows():
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
                return attrs != 0xFFFFFFFF and (attrs & 2)
            except Exception as e:
                logger.debug(f"操作失败: {e}")
                return name.startswith('.')
        else:
            return name.startswith('.')
    
    def get_path_separator(self) -> str:
        return os.sep
    
    def get_line_separator(self) -> str:
        return os.linesep


file_system_adapter = FileSystemAdapter()