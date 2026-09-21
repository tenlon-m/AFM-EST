import json
from pathlib import Path
from typing import Dict, Optional, Callable, List
from enum import Enum
import threading

from core.logger import logger


class Language(Enum):
    CHINESE = "zh_CN"
    ENGLISH = "en_US"
    JAPANESE = "ja_JP"
    KOREAN = "ko_KR"


class LanguageManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._current_language = Language.CHINESE
        self._translations: Dict[str, Dict[str, str]] = {}
        self._fallback_language = Language.ENGLISH
        self._listeners: List[Callable[[Language], None]] = []
        self._initialized = True
        self._translations_dir = Path("resources/translations")
        
        self._load_default_translations()
    
    def _load_default_translations(self) -> None:
        self._translations[Language.CHINESE.value] = {
            "app.name": "AFM-EST 文件管理器",
            "menu.file": "文件",
            "menu.edit": "编辑",
            "menu.view": "查看",
            "menu.tools": "工具",
            "menu.transfer": "传输",
            "menu.compare": "对比",
            "menu.help": "帮助",
            "button.copy": "复制",
            "button.paste": "粘贴",
            "button.delete": "删除",
            "button.compress": "压缩",
            "button.decompress": "解压",
            "button.search": "搜索",
            "label.name": "名称",
            "label.size": "大小",
            "label.type": "类型",
            "label.modified": "修改日期",
            "label.created": "创建日期",
            "theme.light": "浅色",
            "theme.dark": "深色",
            "theme.system": "跟随系统",
            "view.details": "详细信息",
            "view.icons": "图标",
            "view.thumbnails": "缩略图",
            "view.list": "列表",
            "view.tile": "平铺",
            "disk.total_space": "总容量",
            "disk.used_space": "已使用",
            "disk.free_space": "可用空间",
            "quick_access.title": "快速访问",
            "quick_access.pin": "固定",
            "quick_access.unpin": "取消固定",
            "history.title": "历史记录",
            "bookmark.title": "收藏夹",
            "error.file_not_found": "文件未找到",
            "error.permission_denied": "权限不足",
            "error.operation_failed": "操作失败",
        }
        
        self._translations[Language.ENGLISH.value] = {
            "app.name": "AFM-EST File Manager",
            "menu.file": "File",
            "menu.edit": "Edit",
            "menu.view": "View",
            "menu.tools": "Tools",
            "menu.transfer": "Transfer",
            "menu.compare": "Compare",
            "menu.help": "Help",
            "button.copy": "Copy",
            "button.paste": "Paste",
            "button.delete": "Delete",
            "button.compress": "Compress",
            "button.decompress": "Decompress",
            "button.search": "Search",
            "label.name": "Name",
            "label.size": "Size",
            "label.type": "Type",
            "label.modified": "Modified",
            "label.created": "Created",
            "theme.light": "Light",
            "theme.dark": "Dark",
            "theme.system": "System",
            "view.details": "Details",
            "view.icons": "Icons",
            "view.thumbnails": "Thumbnails",
            "view.list": "List",
            "view.tile": "Tile",
            "disk.total_space": "Total Space",
            "disk.used_space": "Used Space",
            "disk.free_space": "Free Space",
            "quick_access.title": "Quick Access",
            "quick_access.pin": "Pin",
            "quick_access.unpin": "Unpin",
            "history.title": "History",
            "bookmark.title": "Bookmarks",
            "error.file_not_found": "File not found",
            "error.permission_denied": "Permission denied",
            "error.operation_failed": "Operation failed",
        }
    
    def load_translations(self, language: Language, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            self._translations[language.value] = translations
        except Exception as e:
            logger.warning(f"加载翻译文件失败: {e}")
    
    def save_translations(self, language: Language, file_path: str) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        translations = self._translations.get(language.value, {})
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存翻译文件失败: {e}")
    
    def set_language(self, language: Language) -> None:
        if language == self._current_language:
            return
        
        self._current_language = language
        self._notify_listeners()
    
    def get_language(self) -> Language:
        return self._current_language
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        translations = self._translations.get(self._current_language.value, {})
        
        if key in translations:
            return translations[key]
        
        fallback_translations = self._translations.get(self._fallback_language.value, {})
        if key in fallback_translations:
            return fallback_translations[key]
        
        return default if default is not None else key
    
    def tr(self, key: str, default: Optional[str] = None) -> str:
        return self.translate(key, default)
    
    def add_listener(self, callback: Callable[[Language], None]) -> None:
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[Language], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        for callback in self._listeners:
            try:
                callback(self._current_language)
            except Exception as e:
                logger.warning(f"语言切换回调失败: {e}")
    
    def get_available_languages(self) -> List[Language]:
        return list(Language)
    
    def get_language_name(self, language: Language) -> str:
        names = {
            Language.CHINESE: "简体中文",
            Language.ENGLISH: "English",
            Language.JAPANESE: "日本語",
            Language.KOREAN: "한국어",
        }
        return names.get(language, language.value)
    
    def add_translation(self, key: str, value: str, language: Optional[Language] = None) -> None:
        lang = language or self._current_language
        if lang.value not in self._translations:
            self._translations[lang.value] = {}
        self._translations[lang.value][key] = value
    
    def get_all_translations(self, language: Optional[Language] = None) -> Dict[str, str]:
        lang = language or self._current_language
        return self._translations.get(lang.value, {}).copy()


language_manager = LanguageManager()