from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import math


@dataclass
class QuickAccessItem:
    path: str
    display_name: str
    is_pinned: bool = False
    access_frequency: int = 0
    last_access_time: Optional[datetime] = None
    is_valid: bool = True
    
    def __post_init__(self):
        if self.last_access_time is None:
            self.last_access_time = datetime.now()
    
    def calculate_score(self) -> float:
        if self.is_pinned:
            return float('inf')
        
        if self.access_frequency == 0:
            return 0.0
        
        now = datetime.now()
        time_diff = (now - self.last_access_time).total_seconds()
        time_decay = math.exp(-time_diff / (7 * 24 * 3600))
        
        frequency_weight = math.log1p(self.access_frequency)
        
        score = frequency_weight * time_decay * 100
        return score
    
    def update_access(self) -> None:
        self.access_frequency += 1
        self.last_access_time = datetime.now()
    
    def check_validity(self) -> bool:
        try:
            path_obj = Path(self.path)
            self.is_valid = path_obj.exists()
            return self.is_valid
        except Exception:
            self.is_valid = False
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'display_name': self.display_name,
            'is_pinned': self.is_pinned,
            'access_frequency': self.access_frequency,
            'last_access_time': self.last_access_time.isoformat() if self.last_access_time else None,
            'is_valid': self.is_valid,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuickAccessItem':
        last_access_time = None
        if data.get('last_access_time'):
            try:
                last_access_time = datetime.fromisoformat(data['last_access_time'])
            except ValueError:
                pass
        
        return cls(
            path=data['path'],
            display_name=data['display_name'],
            is_pinned=data.get('is_pinned', False),
            access_frequency=data.get('access_frequency', 0),
            last_access_time=last_access_time,
            is_valid=data.get('is_valid', True),
        )
    
    @classmethod
    def create_from_path(cls, path: str, is_pinned: bool = False) -> 'QuickAccessItem':
        path_obj = Path(path)
        display_name = path_obj.name or path
        return cls(
            path=str(path_obj.absolute()),
            display_name=display_name,
            is_pinned=is_pinned,
            is_valid=path_obj.exists(),
        )