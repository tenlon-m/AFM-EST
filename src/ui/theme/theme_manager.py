import json
from pathlib import Path
from typing import Dict, Any, Callable, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from models.theme_config import ThemeConfig, ThemeType
from .theme_styles import generate_stylesheet


class ThemeManager(QObject):
    theme_changed = Signal(ThemeConfig)
    
    _instance = None
    
    def __new__(cls, parent=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, parent=None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        super().__init__(parent)
        
        self._current_theme = ThemeConfig.create_light_theme()
        self._config_path = Path("config/theme.json")
        self._listeners: List[Callable[[ThemeConfig], None]] = []
        self._initialized = True
        
        self.load_theme()
    
    def load_theme(self) -> None:
        if not self._config_path.exists():
            self.save_theme()
            return
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._current_theme = ThemeConfig.from_dict(data)
            self._apply_theme()
        
        except Exception:
            self._current_theme = ThemeConfig.create_light_theme()
    
    def save_theme(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self._current_theme.to_dict()
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_theme(self, theme_type: ThemeType) -> None:
        if theme_type == ThemeType.LIGHT:
            self._current_theme = ThemeConfig.create_light_theme()
        elif theme_type == ThemeType.DARK:
            self._current_theme = ThemeConfig.create_dark_theme()
        else:
            self._current_theme = self._get_system_theme()
        
        self._apply_theme()
        self.save_theme()
        self.theme_changed.emit(self._current_theme)
        self._notify_listeners()
    
    def _get_system_theme(self) -> ThemeConfig:
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                bg_color = palette.window().color()
                luminance = (bg_color.red() * 0.299 + bg_color.green() * 0.587 + bg_color.blue() * 0.114)
                
                if luminance < 128:
                    return ThemeConfig.create_dark_theme()
        except Exception:
            pass
        
        return ThemeConfig.create_light_theme()
    
    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            stylesheet = generate_stylesheet(self._current_theme)
            app.setStyleSheet(stylesheet)
    
    def get_current_theme(self) -> ThemeConfig:
        return self._current_theme
    
    def get_theme_type(self) -> ThemeType:
        return self._current_theme.theme_type
    
    def is_dark_theme(self) -> bool:
        return self._current_theme.theme_type == ThemeType.DARK
    
    def toggle_theme(self) -> None:
        if self.is_dark_theme():
            self.set_theme(ThemeType.LIGHT)
        else:
            self.set_theme(ThemeType.DARK)
    
    def add_listener(self, callback: Callable[[ThemeConfig], None]) -> None:
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[ThemeConfig], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        for callback in self._listeners:
            try:
                callback(self._current_theme)
            except Exception:
                pass
    
    def set_corner_radius(self, radius: int) -> None:
        self._current_theme.corner_radius = radius
        self._apply_theme()
        self.save_theme()
    
    def set_mica_enabled(self, enabled: bool) -> None:
        self._current_theme.mica_enabled = enabled
        self._apply_theme()
        self.save_theme()
    
    def get_colors(self) -> Dict[str, str]:
        return self._current_theme.colors.to_dict()
    
    def get_fonts(self) -> Dict[str, Any]:
        return self._current_theme.fonts.to_dict()