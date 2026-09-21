import sys
import os
import platform
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path


class PlatformType(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    KYLIN = "kylin"
    DARWIN = "darwin"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    platform_type: PlatformType
    name: str
    version: str
    arch: str
    path_sep: str
    line_sep: str
    is_case_sensitive: bool
    
    @property
    def is_windows(self) -> bool:
        return self.platform_type == PlatformType.WINDOWS
    
    @property
    def is_linux(self) -> bool:
        return self.platform_type in (PlatformType.LINUX, PlatformType.KYLIN)
    
    @property
    def is_kylin(self) -> bool:
        return self.platform_type == PlatformType.KYLIN


class PlatformDetector:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._platform_info: Optional[PlatformInfo] = None
        self._initialized = True
        self._detect_platform()
    
    def _detect_platform(self) -> None:
        if sys.platform == 'win32':
            platform_type = PlatformType.WINDOWS
            name = "Windows"
            version = platform.version()
            is_case_sensitive = False
        
        elif sys.platform == 'darwin':
            platform_type = PlatformType.DARWIN
            name = "macOS"
            version = platform.mac_ver()[0]
            is_case_sensitive = False
        
        elif sys.platform.startswith('linux'):
            distro_info = self._get_linux_distro()
            
            if distro_info and 'kylin' in distro_info.get('name', '').lower():
                platform_type = PlatformType.KYLIN
                name = distro_info.get('pretty_name', 'Kylin')
                version = distro_info.get('version', 'Unknown')
            else:
                platform_type = PlatformType.LINUX
                name = distro_info.get('name', 'Linux') if distro_info else 'Linux'
                version = distro_info.get('version', 'Unknown') if distro_info else 'Unknown'
            
            is_case_sensitive = True
        
        else:
            platform_type = PlatformType.UNKNOWN
            name = "Unknown"
            version = "Unknown"
            is_case_sensitive = True
        
        self._platform_info = PlatformInfo(
            platform_type=platform_type,
            name=name,
            version=version,
            arch=platform.machine(),
            path_sep=os.sep,
            line_sep=os.linesep,
            is_case_sensitive=is_case_sensitive
        )
    
    def _get_linux_distro(self) -> Optional[Dict[str, str]]:
        os_release_path = Path('/etc/os-release')
        
        if not os_release_path.exists():
            return None
        
        try:
            info = {}
            with open(os_release_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        info[key.lower()] = value
            return info
        except Exception:
            return None
    
    def get_platform_info(self) -> PlatformInfo:
        return self._platform_info
    
    def get_platform_type(self) -> PlatformType:
        return self._platform_info.platform_type
    
    def is_windows(self) -> bool:
        return self._platform_info.is_windows
    
    def is_linux(self) -> bool:
        return self._platform_info.is_linux
    
    def is_kylin(self) -> bool:
        return self._platform_info.is_kylin
    
    def get_temp_directory(self) -> str:
        import tempfile
        return tempfile.gettempdir()
    
    def get_data_directory(self) -> str:
        if self.is_windows():
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return str(Path(appdata) / 'AFM-EST')
        else:
            xdg_data = os.environ.get('XDG_DATA_HOME')
            if xdg_data:
                return str(Path(xdg_data) / 'AFM-EST')
            return str(Path.home() / '.local' / 'share' / 'AFM-EST')
    
    def get_cache_directory(self) -> str:
        if self.is_windows():
            localappdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return str(Path(localappdata) / 'AFM-EST' / 'cache')
        else:
            xdg_cache = os.environ.get('XDG_CACHE_HOME')
            if xdg_cache:
                return str(Path(xdg_cache) / 'AFM-EST')
            return str(Path.home() / '.cache' / 'AFM-EST')
    
    def get_config_directory(self) -> str:
        if self.is_windows():
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return str(Path(appdata) / 'AFM-EST' / 'config')
        else:
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                return str(Path(xdg_config) / 'AFM-EST')
            return str(Path.home() / '.config' / 'AFM-EST')
    
    def get_platform_directories(self) -> Dict[str, str]:
        return {
            'home': str(Path.home()),
            'temp': self.get_temp_directory(),
            'data': self.get_data_directory(),
            'cache': self.get_cache_directory(),
            'config': self.get_config_directory(),
        }


platform_detector = PlatformDetector()