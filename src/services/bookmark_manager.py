import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class BookmarkManager:
    def __init__(self, file_path: str = "config/bookmarks.json"):
        self._file_path = Path(file_path)
        self._bookmarks: List[Dict[str, Any]] = []
        self.load()
    
    def add(self, path: str, name: Optional[str] = None) -> bool:
        if self.exists(path):
            return False
        
        path_obj = Path(path)
        bookmark = {
            'path': str(path_obj.absolute()),
            'name': name or path_obj.name,
            'added_time': datetime.now().isoformat(),
        }
        
        self._bookmarks.append(bookmark)
        self.save()
        return True
    
    def remove(self, path: str) -> bool:
        for i, bookmark in enumerate(self._bookmarks):
            if bookmark['path'] == path:
                self._bookmarks.pop(i)
                self.save()
                return True
        return False
    
    def exists(self, path: str) -> bool:
        return any(b['path'] == path for b in self._bookmarks)
    
    def get_all(self) -> List[Dict[str, Any]]:
        return self._bookmarks.copy()
    
    def get_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        for bookmark in self._bookmarks:
            if bookmark['path'] == path:
                return bookmark
        return None
    
    def rename(self, path: str, new_name: str) -> bool:
        for bookmark in self._bookmarks:
            if bookmark['path'] == path:
                bookmark['name'] = new_name
                self.save()
                return True
        return False
    
    def sort_by_name(self) -> None:
        self._bookmarks.sort(key=lambda b: b['name'].lower())
        self.save()
    
    def sort_by_time(self) -> None:
        self._bookmarks.sort(key=lambda b: b['added_time'], reverse=True)
        self.save()
    
    def clear(self) -> None:
        self._bookmarks.clear()
        self.save()
    
    def save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self._file_path, 'w', encoding='utf-8') as f:
            json.dump(self._bookmarks, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        if not self._file_path.exists():
            self._bookmarks = []
            return
        
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                self._bookmarks = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._bookmarks = []
    
    def __len__(self) -> int:
        return len(self._bookmarks)
    
    def __iter__(self):
        return iter(self._bookmarks)