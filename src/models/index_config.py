from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import os
import sys


class IndexStatus(Enum):
    NOT_INDEXED = "not_indexed"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class DriveType(Enum):
    FIXED = "fixed"
    REMOVABLE = "removable"
    NETWORK = "network"
    CDROM = "cdrom"
    RAM = "ram"


@dataclass
class DiskIndexInfo:
    drive_path: str
    status: IndexStatus = IndexStatus.NOT_INDEXED
    file_count: int = 0
    index_size: int = 0
    last_index_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.drive_path:
            raise ValueError("Drive path cannot be empty")
        if self.file_count < 0:
            raise ValueError(f"File count cannot be negative: {self.file_count}")
        if self.index_size < 0:
            raise ValueError(f"Index size cannot be negative: {self.index_size}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'drive_path': self.drive_path,
            'status': self.status.value,
            'file_count': self.file_count,
            'index_size': self.index_size,
            'last_index_time': self.last_index_time.isoformat() if self.last_index_time else None,
            'error_message': self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiskIndexInfo':
        last_index_time = None
        if data.get('last_index_time'):
            try:
                last_index_time = datetime.fromisoformat(data['last_index_time'])
            except ValueError:
                pass
        
        return cls(
            drive_path=data['drive_path'],
            status=IndexStatus(data.get('status', 'not_indexed')),
            file_count=data.get('file_count', 0),
            index_size=data.get('index_size', 0),
            last_index_time=last_index_time,
            error_message=data.get('error_message'),
        )
    
    def is_indexed(self) -> bool:
        return self.status == IndexStatus.COMPLETED
    
    def is_indexing(self) -> bool:
        return self.status == IndexStatus.INDEXING
    
    def mark_completed(self, file_count: int, index_size: int) -> None:
        self.status = IndexStatus.COMPLETED
        self.file_count = file_count
        self.index_size = index_size
        self.last_index_time = datetime.now()
        self.error_message = None
    
    def mark_failed(self, error_message: str) -> None:
        self.status = IndexStatus.FAILED
        self.error_message = error_message


@dataclass
class IndexProgress:
    total_files: int = 0
    processed_files: int = 0
    current_file: Optional[str] = None
    start_time: Optional[datetime] = None
    estimated_remaining_seconds: float = 0.0
    
    @property
    def progress_percentage(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def is_completed(self) -> bool:
        return self.processed_files >= self.total_files and self.total_files > 0
    
    def update_progress(self, processed_files: int, current_file: Optional[str] = None) -> None:
        self.processed_files = processed_files
        self.current_file = current_file
        
        if self.start_time and processed_files > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                speed = processed_files / elapsed
                remaining_files = self.total_files - processed_files
                self.estimated_remaining_seconds = remaining_files / speed if speed > 0 else 0
    
    def start(self, total_files: int) -> None:
        self.total_files = total_files
        self.processed_files = 0
        self.start_time = datetime.now()
        self.current_file = None
        self.estimated_remaining_seconds = 0.0


@dataclass
class IndexConfig:
    indexed_disks: Dict[str, DiskIndexInfo] = field(default_factory=dict)
    index_location: str = ""
    auto_detect_new_disks: bool = True
    last_full_index_time: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.index_location:
            self.index_location = self._get_default_location()
    
    @staticmethod
    def _get_default_location() -> str:
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return str(Path(appdata) / 'AFM-EST' / 'index')
        elif sys.platform == 'darwin':
            return str(Path.home() / 'Library' / 'Application Support' / 'AFM-EST' / 'index')
        else:
            return str(Path.home() / '.local' / 'share' / 'AFM-EST' / 'index')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'indexed_disks': {
                path: info.to_dict() for path, info in self.indexed_disks.items()
            },
            'index_location': self.index_location,
            'auto_detect_new_disks': self.auto_detect_new_disks,
            'last_full_index_time': self.last_full_index_time.isoformat() if self.last_full_index_time else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndexConfig':
        indexed_disks = {
            path: DiskIndexInfo.from_dict(info)
            for path, info in data.get('indexed_disks', {}).items()
        }
        
        last_full_index_time = None
        if data.get('last_full_index_time'):
            try:
                last_full_index_time = datetime.fromisoformat(data['last_full_index_time'])
            except ValueError:
                pass
        
        return cls(
            indexed_disks=indexed_disks,
            index_location=data.get('index_location', cls._get_default_location()),
            auto_detect_new_disks=data.get('auto_detect_new_disks', True),
            last_full_index_time=last_full_index_time,
        )
    
    def get_disk_index_info(self, drive_path: str) -> Optional[DiskIndexInfo]:
        return self.indexed_disks.get(drive_path)
    
    def update_disk_index_info(self, info: DiskIndexInfo) -> None:
        self.indexed_disks[info.drive_path] = info
    
    def remove_disk_index_info(self, drive_path: str) -> bool:
        if drive_path in self.indexed_disks:
            del self.indexed_disks[drive_path]
            return True
        return False
    
    def get_indexed_disks(self) -> List[str]:
        return [
            path for path, info in self.indexed_disks.items()
            if info.is_indexed()
        ]
    
    def get_total_index_size(self) -> int:
        return sum(info.index_size for info in self.indexed_disks.values())
    
    def get_total_file_count(self) -> int:
        return sum(info.file_count for info in self.indexed_disks.values())