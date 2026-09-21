try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from pathlib import Path
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
import threading


class ConfigService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._config_path = config_path or "config/config.yaml"
        self._config: Dict[str, Any] = {}
        self._listeners: List[Callable] = []
        self._last_modified: Optional[datetime] = None
        self._initialized = True
        
        self.load()
    
    def load(self) -> None:
        path = Path(self._config_path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            self._config = self._get_default_config()
            self.save()
            return
        
        if not HAS_YAML:
            self._config = self._get_default_config()
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            self._last_modified = datetime.fromtimestamp(path.stat().st_mtime)
        except Exception as e:
            self._config = self._get_default_config()
    
    def save(self) -> None:
        if not HAS_YAML:
            return
        
        path = Path(self._config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save_immediately: bool = True) -> None:
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        if save_immediately:
            self.save()
            self._notify_listeners(key, value)
    
    def add_listener(self, callback: Callable[[str, Any], None]) -> None:
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[str, Any], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, key: str, value: Any) -> None:
        for callback in self._listeners:
            try:
                callback(key, value)
            except Exception as e:
                logger.debug(f"配置变更回调失败: {e}")
    
    def check_for_reload(self) -> bool:
        path = Path(self._config_path)
        if not path.exists():
            return False
        
        modified_time = datetime.fromtimestamp(path.stat().st_mtime)
        if self._last_modified and modified_time > self._last_modified:
            self.load()
            return True
        return False
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        return {
            'version': '1.0',
            'ui': {
                'theme': 'light',
                'view_mode': 'details',
                'icon_size': 32,
                'show_hidden_files': False,
                'window_size': [1200, 800],
            },
            'search': {
                'index_path': 'index',
                'max_threads': 4,
            },
            'transfer': {
                'buffer_size': 8192,
                'max_retries': 3,
            },
            'quick_access': {
                'max_items': 20,
                'show_recent': True,
            },
        }
    
    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()
    
    def update(self, config: Dict[str, Any], save_immediately: bool = True) -> None:
        self._config.update(config)
        if save_immediately:
            self.save()