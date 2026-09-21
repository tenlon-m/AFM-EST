from typing import Dict, List, Optional, Callable, Any
from abc import ABC, abstractmethod
import os
import json
import importlib.util
import threading

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class PluginBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    def author(self) -> str:
        return "Unknown"
    
    @property
    def dependencies(self) -> List[str]:
        return []
    
    @abstractmethod
    def on_load(self, plugin_manager: 'PluginManager') -> None:
        pass
    
    @abstractmethod
    def on_unload(self) -> None:
        pass
    
    def on_enable(self) -> None:
        pass
    
    def on_disable(self) -> None:
        pass


class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self._plugins_dir = plugins_dir
        self._plugins: Dict[str, PluginBase] = {}
        self._enabled: Dict[str, bool] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        
        os.makedirs(plugins_dir, exist_ok=True)
        
        logger.info(f"插件管理器已初始化，插件目录: {plugins_dir}")
    
    def discover_plugins(self) -> List[str]:
        discovered = []
        
        if not os.path.exists(self._plugins_dir):
            return discovered
        
        for item in os.listdir(self._plugins_dir):
            plugin_path = os.path.join(self._plugins_dir, item)
            
            if os.path.isdir(plugin_path):
                init_file = os.path.join(plugin_path, "__init__.py")
                if os.path.exists(init_file):
                    discovered.append(item)
            
            elif item.endswith(".py") and item != "__init__.py":
                discovered.append(item[:-3])
        
        logger.info(f"发现 {len(discovered)} 个插件: {discovered}")
        return discovered
    
    def load_plugin(self, plugin_name: str) -> bool:
        with self._lock:
            if plugin_name in self._plugins:
                logger.warning(f"插件已加载: {plugin_name}")
                return False
            
            try:
                plugin_path = os.path.join(self._plugins_dir, plugin_name)
                
                if os.path.isdir(plugin_path):
                    module_path = os.path.join(plugin_path, "__init__.py")
                else:
                    module_path = plugin_path + ".py"
                
                if not os.path.exists(module_path):
                    logger.error(f"插件文件不存在: {module_path}")
                    return False
                
                spec = importlib.util.spec_from_file_location(plugin_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'Plugin'):
                    plugin_class = module.Plugin
                    plugin_instance = plugin_class()
                    
                    if isinstance(plugin_instance, PluginBase):
                        plugin_instance.on_load(self)
                        
                        self._plugins[plugin_name] = plugin_instance
                        self._enabled[plugin_name] = True
                        
                        logger.info(f"插件加载成功: {plugin_name} v{plugin_instance.version}")
                        return True
                    else:
                        logger.error(f"插件类未继承PluginBase: {plugin_name}")
                        return False
                else:
                    logger.error(f"插件模块未定义Plugin类: {plugin_name}")
                    return False
                    
            except Exception as e:
                logger.error(f"加载插件失败 {plugin_name}: {e}")
                return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        with self._lock:
            if plugin_name not in self._plugins:
                logger.warning(f"插件未加载: {plugin_name}")
                return False
            
            try:
                plugin = self._plugins[plugin_name]
                plugin.on_unload()
                
                del self._plugins[plugin_name]
                del self._enabled[plugin_name]
                
                for hook_name in list(self._hooks.keys()):
                    self._hooks[hook_name] = [
                        callback for callback in self._hooks[hook_name]
                        if callback.__module__ != plugin_name
                    ]
                
                logger.info(f"插件卸载成功: {plugin_name}")
                return True
                
            except Exception as e:
                logger.error(f"卸载插件失败 {plugin_name}: {e}")
                return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        with self._lock:
            if plugin_name not in self._plugins:
                logger.warning(f"插件未加载: {plugin_name}")
                return False
            
            if self._enabled.get(plugin_name, False):
                logger.warning(f"插件已启用: {plugin_name}")
                return False
            
            try:
                self._plugins[plugin_name].on_enable()
                self._enabled[plugin_name] = True
                logger.info(f"插件已启用: {plugin_name}")
                return True
            except Exception as e:
                logger.error(f"启用插件失败 {plugin_name}: {e}")
                return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        with self._lock:
            if plugin_name not in self._plugins:
                logger.warning(f"插件未加载: {plugin_name}")
                return False
            
            if not self._enabled.get(plugin_name, False):
                logger.warning(f"插件已禁用: {plugin_name}")
                return False
            
            try:
                self._plugins[plugin_name].on_disable()
                self._enabled[plugin_name] = False
                logger.info(f"插件已禁用: {plugin_name}")
                return True
            except Exception as e:
                logger.error(f"禁用插件失败 {plugin_name}: {e}")
                return False
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        with self._lock:
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            
            self._hooks[hook_name].append(callback)
        logger.info(f"注册钩子: {hook_name} -> {callback.__name__}")
    
    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        with self._lock:
            if hook_name in self._hooks:
                self._hooks[hook_name] = [
                    cb for cb in self._hooks[hook_name] if cb != callback
                ]
        logger.info(f"注销钩子: {hook_name} -> {callback.__name__}")
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        with self._lock:
            callbacks = list(self._hooks.get(hook_name, []))
        
        results = []
        for callback in callbacks:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"执行钩子失败 {hook_name} -> {callback.__name__}: {e}")
        
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        with self._lock:
            return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        with self._lock:
            return self._plugins.copy()
    
    def is_enabled(self, plugin_name: str) -> bool:
        with self._lock:
            return self._enabled.get(plugin_name, False)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return None
        
        return {
            'name': plugin.name,
            'version': plugin.version,
            'description': plugin.description,
            'author': plugin.author,
            'dependencies': plugin.dependencies,
            'enabled': self.is_enabled(plugin_name)
        }


plugin_manager = PluginManager()