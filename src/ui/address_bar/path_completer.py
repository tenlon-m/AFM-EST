from typing import List
from pathlib import Path

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QCompleter


class PathCompleter(QCompleter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._model = QStringListModel(self)
        self.setModel(self._model)
        
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterMode(Qt.MatchContains)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setWrapAround(False)
    
    def update_completions(self, partial_path: str) -> None:
        if not partial_path:
            self._model.setStringList([])
            return
        
        completions = self._get_path_completions(partial_path)
        self._model.setStringList(completions)
    
    def _get_path_completions(self, partial_path: str) -> List[str]:
        completions = []
        
        try:
            path = Path(partial_path)
            
            if path.is_absolute():
                parent = path.parent
                prefix = path.name
                
                if parent.exists() and parent.is_dir():
                    for item in parent.iterdir():
                        if item.name.lower().startswith(prefix.lower()):
                            completions.append(str(item))
            
            else:
                cwd = Path.cwd()
                for item in cwd.iterdir():
                    if item.name.lower().startswith(partial_path.lower()):
                        completions.append(str(item))
        
        except (OSError, PermissionError):
            pass
        
        completions.sort(key=lambda p: Path(p).name.lower())
        
        return completions[:20]
    
    def set_history(self, history_paths: List[str]) -> None:
        current_list = self._model.stringList()
        combined = list(set(current_list + history_paths))
        combined.sort()
        self._model.setStringList(combined)
    
    def add_path(self, path: str) -> None:
        current_list = self._model.stringList()
        if path not in current_list:
            current_list.append(path)
            self._model.setStringList(current_list)