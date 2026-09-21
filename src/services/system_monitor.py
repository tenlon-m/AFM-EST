try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
import platform
import threading
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal, QTimer

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class SystemMonitor(QObject):
    cpu_usage_changed = Signal(float)
    memory_usage_changed = Signal(float, float, float)
    disk_usage_changed = Signal(str, float, float, float)
    
    def __init__(self, update_interval: int = 1000, parent=None):
        super().__init__(parent)
        
        self._update_interval = update_interval
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        
        self._last_cpu_percent: Optional[float] = None
        self._monitoring = False
        
        self._disk_paths: list = []
        self._lock = threading.Lock()
    
    def start_monitoring(self) -> None:
        with self._lock:
            if self._monitoring:
                return
            
            self._monitoring = True
            self._timer.start(self._update_interval)
            logger.info(f"系统监控已启动，更新间隔: {self._update_interval}ms")
    
    def stop_monitoring(self) -> None:
        with self._lock:
            if not self._monitoring:
                return
            
            self._monitoring = False
            self._timer.stop()
            logger.info("系统监控已停止")
    
    def set_update_interval(self, interval: int) -> None:
        with self._lock:
            self._update_interval = interval
            if self._monitoring:
                self._timer.setInterval(interval)
    
    def add_disk_monitor(self, path: str) -> None:
        with self._lock:
            if path not in self._disk_paths:
                self._disk_paths.append(path)
    
    def remove_disk_monitor(self, path: str) -> None:
        with self._lock:
            if path in self._disk_paths:
                self._disk_paths.remove(path)
    
    def _update(self) -> None:
        if not HAS_PSUTIL:
            return
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            if cpu_percent is not None:
                self._last_cpu_percent = cpu_percent
                self.cpu_usage_changed.emit(cpu_percent)
        except Exception as e:
            logger.warning(f"获取CPU使用率失败: {e}")
        
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024 ** 3)
            used_gb = memory.used / (1024 ** 3)
            percent = memory.percent
            self.memory_usage_changed.emit(total_gb, used_gb, percent)
        except Exception as e:
            logger.warning(f"获取内存使用率失败: {e}")
        
        with self._lock:
            disk_paths_copy = list(self._disk_paths)
        
        for path in disk_paths_copy:
            try:
                disk_usage = psutil.disk_usage(path)
                total_gb = disk_usage.total / (1024 ** 3)
                used_gb = disk_usage.used / (1024 ** 3)
                percent = disk_usage.percent
                self.disk_usage_changed.emit(path, total_gb, used_gb, percent)
            except Exception as e:
                logger.warning(f"获取磁盘使用率失败 {path}: {e}")
    
    @staticmethod
    def get_cpu_usage() -> float:
        if not HAS_PSUTIL:
            return 0.0
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0.0
    
    @staticmethod
    def get_memory_usage() -> Tuple[float, float, float]:
        if not HAS_PSUTIL:
            return 0.0, 0.0, 0.0
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024 ** 3)
            used_gb = memory.used / (1024 ** 3)
            percent = memory.percent
            return total_gb, used_gb, percent
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0.0, 0.0, 0.0
    
    @staticmethod
    def get_disk_usage(path: str) -> Tuple[float, float, float]:
        if not HAS_PSUTIL:
            return 0.0, 0.0, 0.0
        try:
            disk_usage = psutil.disk_usage(path)
            total_gb = disk_usage.total / (1024 ** 3)
            used_gb = disk_usage.used / (1024 ** 3)
            percent = disk_usage.percent
            return total_gb, used_gb, percent
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 0.0, 0.0, 0.0
    
    @staticmethod
    def get_system_info() -> dict:
        if not HAS_PSUTIL:
            return {}
        try:
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            memory = psutil.virtual_memory()
            total_memory_gb = memory.total / (1024 ** 3)
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'cpu_count': cpu_count,
                'cpu_count_logical': cpu_count_logical,
                'total_memory_gb': total_memory_gb,
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}
    
    def is_monitoring(self) -> bool:
        return self._monitoring
    
    def get_last_cpu_percent(self) -> Optional[float]:
        return self._last_cpu_percent