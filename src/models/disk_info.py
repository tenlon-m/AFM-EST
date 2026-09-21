from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import re


class DriveType(Enum):
    FIXED = "fixed"
    REMOVABLE = "removable"
    NETWORK = "network"
    CDROM = "cdrom"
    RAM = "ram"
    UNKNOWN = "unknown"


class IndexStatus(Enum):
    NOT_INDEXED = "not_indexed"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DiskInfo:
    drive_letter: str
    display_name: str
    drive_type: DriveType
    total_space: int
    used_space: int
    free_space: int
    file_system: str = ""
    is_ready: bool = True
    icon_path: Optional[str] = None
    index_status: IndexStatus = IndexStatus.NOT_INDEXED
    indexed_file_count: int = 0
    index_size: int = 0
    
    def __post_init__(self):
        self._validate()
    
    def _validate(self):
        # 支持多种格式：A: 或 A:\
        drive_letter = self.drive_letter.rstrip('\\')
        if not re.match(r'^[A-Z]:$', drive_letter):
            raise ValueError(f"Invalid drive letter format: {self.drive_letter}")
        # 标准化为 A: 格式
        self.drive_letter = drive_letter
        if self.total_space < 0:
            raise ValueError(f"Total space cannot be negative: {self.total_space}")
        if self.used_space < 0:
            raise ValueError(f"Used space cannot be negative: {self.used_space}")
        if self.free_space < 0:
            raise ValueError(f"Free space cannot be negative: {self.free_space}")
        if self.used_space > self.total_space:
            raise ValueError(f"Used space ({self.used_space}) cannot exceed total space ({self.total_space})")
    
    @property
    def usage_percentage(self) -> float:
        if self.total_space == 0:
            return 0.0
        return (self.used_space / self.total_space) * 100
    
    @property
    def usage_level(self) -> str:
        percentage = self.usage_percentage
        if percentage < 70:
            return "low"
        elif percentage < 90:
            return "medium"
        else:
            return "high"
    
    @property
    def path(self) -> str:
        """获取磁盘路径（drive_letter + \）"""
        return self.drive_letter + '\\'
    

    def to_dict(self) -> Dict[str, Any]:
        return {
            'drive_letter': self.drive_letter,
            'display_name': self.display_name,
            'drive_type': self.drive_type.value,
            'total_space': self.total_space,
            'used_space': self.used_space,
            'free_space': self.free_space,
            'file_system': self.file_system,
            'is_ready': self.is_ready,
            'icon_path': self.icon_path,
            'index_status': self.index_status.value,
            'indexed_file_count': self.indexed_file_count,
            'index_size': self.index_size,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiskInfo':
        return cls(
            drive_letter=data['drive_letter'],
            display_name=data['display_name'],
            drive_type=DriveType(data['drive_type']),
            total_space=data['total_space'],
            used_space=data['used_space'],
            free_space=data['free_space'],
            file_system=data.get('file_system', ''),
            is_ready=data.get('is_ready', True),
            icon_path=data.get('icon_path'),
            index_status=IndexStatus(data.get('index_status', 'not_indexed')),
            indexed_file_count=data.get('indexed_file_count', 0),
            index_size=data.get('index_size', 0),
        )
    
    def format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    @property
    def formatted_total(self) -> str:
        return self.format_size(self.total_space)
    
    @property
    def formatted_used(self) -> str:
        return self.format_size(self.used_space)
    
    @property
    def formatted_free(self) -> str:
        return self.format_size(self.free_space)
    
    def is_indexable(self) -> bool:
        if not self.is_ready:
            return False
        if self.drive_type in (DriveType.CDROM, DriveType.NETWORK, DriveType.RAM):
            return False
        return True
    
    def is_indexed(self) -> bool:
        return self.index_status == IndexStatus.COMPLETED
    
    def is_indexing(self) -> bool:
        return self.index_status == IndexStatus.INDEXING