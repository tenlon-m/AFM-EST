try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading

from models.index_config import IndexConfig, DiskIndexInfo, IndexStatus


class IndexConfigService:
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
        
        self._config_path = config_path or "config/index_config.yaml"
        self._config: Optional[IndexConfig] = None
        self._initialized = True
        
        self.load()
    
    def load(self) -> None:
        path = Path(self._config_path)
        
        if not path.exists():
            self._config = IndexConfig()
            self.save()
            return
        
        if not HAS_YAML:
            self._config = IndexConfig()
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            self._config = IndexConfig.from_dict(data)
        except Exception as e:
            self._config = IndexConfig()
            self._save_backup()
    
    def save(self) -> None:
        if not HAS_YAML:
            return
        
        path = Path(self._config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self._config.to_dict()
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def _save_backup(self) -> None:
        path = Path(self._config_path)
        if not path.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.parent / f"index_config_backup_{timestamp}.yaml"
        
        try:
            shutil.copy2(path, backup_path)
        except Exception as e:
            logger.debug(f"备份索引配置失败: {e}")
    
    def get_config(self) -> IndexConfig:
        return self._config
    
    def get_index_location(self) -> str:
        return self._config.index_location
    
    def set_index_location(self, location: str) -> None:
        self._config.index_location = location
        self.save()
    
    def get_disk_index_info(self, drive_path: str) -> Optional[DiskIndexInfo]:
        return self._config.get_disk_index_info(drive_path)
    
    def update_disk_index_info(self, info: DiskIndexInfo) -> None:
        self._config.update_disk_index_info(info)
        self.save()
    
    def remove_disk_index_info(self, drive_path: str) -> bool:
        result = self._config.remove_disk_index_info(drive_path)
        if result:
            self.save()
        return result
    
    def get_indexed_disks(self) -> List[str]:
        return self._config.get_indexed_disks()
    
    def get_total_index_size(self) -> int:
        return self._config.get_total_index_size()
    
    def get_total_file_count(self) -> int:
        return self._config.get_total_file_count()
    
    def is_disk_indexed(self, drive_path: str) -> bool:
        info = self.get_disk_index_info(drive_path)
        return info is not None and info.is_indexed()
    
    def mark_disk_indexing(self, drive_path: str) -> None:
        info = self.get_disk_index_info(drive_path) or DiskIndexInfo(drive_path=drive_path)
        info.status = IndexStatus.INDEXING
        self.update_disk_index_info(info)
    
    def mark_disk_completed(self, drive_path: str, file_count: int, index_size: int) -> None:
        info = self.get_disk_index_info(drive_path) or DiskIndexInfo(drive_path=drive_path)
        info.mark_completed(file_count, index_size)
        self.update_disk_index_info(info)
    
    def mark_disk_failed(self, drive_path: str, error_message: str) -> None:
        info = self.get_disk_index_info(drive_path) or DiskIndexInfo(drive_path=drive_path)
        info.mark_failed(error_message)
        self.update_disk_index_info(info)
    
    def get_auto_detect_new_disks(self) -> bool:
        return self._config.auto_detect_new_disks
    
    def set_auto_detect_new_disks(self, enabled: bool) -> None:
        self._config.auto_detect_new_disks = enabled
        self.save()