import json
from pathlib import Path
from typing import List, Optional

from models.quick_access import QuickAccessItem


class QuickAccessManager:
    DEFAULT_MAX_ITEMS = 20
    
    def __init__(self, file_path: str = "config/quick_access.json", max_items: int = DEFAULT_MAX_ITEMS):
        self._file_path = Path(file_path)
        self._max_items = max_items
        self._items: List[QuickAccessItem] = []
        self._pinned_paths: set = set()
        
        self.load()
    
    def add_access(self, path: str) -> None:
        existing = self._find_by_path(path)
        
        if existing:
            existing.update_access()
        else:
            item = QuickAccessItem.create_from_path(path)
            self._items.append(item)
        
        self._cleanup_recent_items()
        self.save()
    
    def pin_folder(self, path: str) -> bool:
        item = self._find_by_path(path)
        
        if item:
            item.is_pinned = True
            self._pinned_paths.add(path)
        else:
            item = QuickAccessItem.create_from_path(path, is_pinned=True)
            self._items.append(item)
            self._pinned_paths.add(path)
        
        self.save()
        return True
    
    def unpin_folder(self, path: str) -> bool:
        item = self._find_by_path(path)
        
        if item and item.is_pinned:
            item.is_pinned = False
            self._pinned_paths.discard(path)
            self.save()
            return True
        
        return False
    
    def is_pinned(self, path: str) -> bool:
        return path in self._pinned_paths
    
    def get_sorted_items(self) -> List[QuickAccessItem]:
        pinned = [item for item in self._items if item.is_pinned]
        recent = [item for item in self._items if not item.is_pinned]
        
        pinned.sort(key=lambda x: x.display_name.lower())
        recent.sort(key=lambda x: x.calculate_score(), reverse=True)
        
        return pinned + recent
    
    def get_pinned_items(self) -> List[QuickAccessItem]:
        return [item for item in self._items if item.is_pinned]
    
    def get_recent_items(self, count: int = 10) -> List[QuickAccessItem]:
        recent = [item for item in self._items if not item.is_pinned]
        recent.sort(key=lambda x: x.calculate_score(), reverse=True)
        return recent[:count]
    
    def remove_item(self, path: str) -> bool:
        for i, item in enumerate(self._items):
            if item.path == path:
                self._items.pop(i)
                self._pinned_paths.discard(path)
                self.save()
                return True
        return False
    
    def remove_invalid_items(self) -> int:
        invalid_items = [
            item for item in self._items
            if not item.check_validity()
        ]
        
        for item in invalid_items:
            self._items.remove(item)
            self._pinned_paths.discard(item.path)
        
        if invalid_items:
            self.save()
        
        return len(invalid_items)
    
    def clear_recent(self) -> None:
        self._items = [item for item in self._items if item.is_pinned]
        self.save()
    
    def clear_all(self) -> None:
        self._items.clear()
        self._pinned_paths.clear()
        self.save()
    
    def _find_by_path(self, path: str) -> Optional[QuickAccessItem]:
        for item in self._items:
            if item.path == path:
                return item
        return None
    
    def _cleanup_recent_items(self) -> None:
        recent = [item for item in self._items if not item.is_pinned]
        
        if len(recent) > self._max_items:
            recent.sort(key=lambda x: x.calculate_score(), reverse=True)
            items_to_remove = recent[self._max_items:]
            
            for item in items_to_remove:
                self._items.remove(item)
    
    def save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'items': [item.to_dict() for item in self._items],
            'max_items': self._max_items,
        }
        
        with open(self._file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        if not self._file_path.exists():
            return
        
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._max_items = data.get('max_items', self.DEFAULT_MAX_ITEMS)
            self._items = [
                QuickAccessItem.from_dict(item_data)
                for item_data in data.get('items', [])
            ]
            
            self._pinned_paths = {item.path for item in self._items if item.is_pinned}
        
        except (json.JSONDecodeError, KeyError, ValueError):
            self._items = []
            self._pinned_paths = set()
    
    def __len__(self) -> int:
        return len(self._items)
    
    def __iter__(self):
        return iter(self.get_sorted_items())