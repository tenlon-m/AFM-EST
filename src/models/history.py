from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


@dataclass
class HistoryItem:
    path: str
    timestamp: datetime
    visit_count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'timestamp': self.timestamp.isoformat(),
            'visit_count': self.visit_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoryItem':
        return cls(
            path=data['path'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            visit_count=data.get('visit_count', 1),
        )
    
    def update_visit(self):
        self.timestamp = datetime.now()
        self.visit_count += 1


class HistoryManager:
    MAX_HISTORY_SIZE = 20
    
    def __init__(self, max_size: int = MAX_HISTORY_SIZE):
        self.max_size = max_size
        self._history: List[HistoryItem] = []
    
    def add(self, path: str) -> None:
        existing_item = self.find_by_path(path)
        if existing_item:
            existing_item.update_visit()
            self._history.remove(existing_item)
            self._history.insert(0, existing_item)
        else:
            new_item = HistoryItem(path=path, timestamp=datetime.now())
            self._history.insert(0, new_item)
            if len(self._history) > self.max_size:
                self._history.pop()
    
    def find_by_path(self, path: str) -> Optional[HistoryItem]:
        for item in self._history:
            if item.path == path:
                return item
        return None
    
    def get_all(self) -> List[HistoryItem]:
        return self._history.copy()
    
    def get_recent(self, count: int = 10) -> List[HistoryItem]:
        return self._history[:count]
    
    def clear(self) -> None:
        self._history.clear()
    
    def remove(self, path: str) -> bool:
        item = self.find_by_path(path)
        if item:
            self._history.remove(item)
            return True
        return False
    
    def save(self, file_path: str) -> None:
        path_obj = Path(file_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'history': [item.to_dict() for item in self._history],
            'max_size': self.max_size,
        }
        
        with open(path_obj, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, file_path: str) -> None:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return
        
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.max_size = data.get('max_size', self.MAX_HISTORY_SIZE)
            self._history = [
                HistoryItem.from_dict(item_data)
                for item_data in data.get('history', [])
            ]
        except (json.JSONDecodeError, KeyError, ValueError):
            self._history = []
    
    def __len__(self) -> int:
        return len(self._history)
    
    def __iter__(self):
        return iter(self._history)