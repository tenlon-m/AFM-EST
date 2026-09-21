from typing import Optional, Dict, List
from PySide6.QtCore import QObject, Signal, QTimer

try:
    from services.transfer_manager import TransferManager
    HAS_TRANSFER_MANAGER = True
except ImportError:
    HAS_TRANSFER_MANAGER = False

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class TransferMonitor(QObject):
    transfer_status_changed = Signal(str)
    transfer_progress_changed = Signal(str, int, int, float)
    transfer_completed = Signal(str, bool, str)
    
    def __init__(self, update_interval: int = 1000, parent=None):
        super().__init__(parent)
        
        self._update_interval = update_interval
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        
        self._transfer_manager: Optional[TransferManager] = None
        self._monitoring = False
        
        self._active_tasks: Dict[str, Dict] = {}
        self._last_status: str = "无任务"
    
    def set_transfer_manager(self, manager: Optional[TransferManager]) -> None:
        self._transfer_manager = manager
    
    def start_monitoring(self) -> None:
        if self._monitoring:
            return
        
        self._monitoring = True
        self._timer.start(self._update_interval)
        logger.info(f"传输监控已启动，更新间隔: {self._update_interval}ms")
    
    def stop_monitoring(self) -> None:
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._timer.stop()
        logger.info("传输监控已停止")
    
    def set_update_interval(self, interval: int) -> None:
        self._update_interval = interval
        if self._monitoring:
            self._timer.setInterval(interval)
    
    def _update(self) -> None:
        if not self._transfer_manager:
            self._update_status_no_manager()
            return
        
        try:
            active_tasks = self._get_active_tasks()
            
            if not active_tasks:
                status = "无任务"
            else:
                running_count = sum(1 for t in active_tasks.values() if t.get('status') == 'running')
                pending_count = sum(1 for t in active_tasks.values() if t.get('status') == 'pending')
                
                if running_count > 0:
                    task = next((t for t in active_tasks.values() if t.get('status') == 'running'), None)
                    if task:
                        progress = task.get('progress', 0)
                        speed = task.get('speed', 0)
                        speed_str = self._format_speed(speed)
                        status = f"传输中 {progress}% | {speed_str}"
                    else:
                        status = f"传输中 ({running_count}个任务)"
                elif pending_count > 0:
                    status = f"等待中 ({pending_count}个任务)"
                else:
                    status = f"{len(active_tasks)}个任务"
            
            if status != self._last_status:
                self._last_status = status
                self.transfer_status_changed.emit(status)
            
            for task_id, task_info in active_tasks.items():
                if task_info.get('status') == 'running':
                    progress = task_info.get('progress', 0)
                    total_size = task_info.get('total_size', 0)
                    speed = task_info.get('speed', 0)
                    self.transfer_progress_changed.emit(task_id, progress, total_size, speed)
        
        except Exception as e:
            logger.warning(f"更新传输状态失败: {e}")
    
    def _get_active_tasks(self) -> Dict[str, Dict]:
        if not self._transfer_manager:
            return {}
        
        try:
            if hasattr(self._transfer_manager, 'get_active_tasks'):
                return self._transfer_manager.get_active_tasks()
            elif hasattr(self._transfer_manager, 'tasks'):
                return {t.task_id: t.to_dict() for t in self._transfer_manager.tasks.values() 
                        if t.status in ['pending', 'running']}
            else:
                return {}
        except Exception as e:
            logger.warning(f"获取活动任务失败: {e}")
            return {}
    
    def _update_status_no_manager(self) -> None:
        status = "无任务"
        if status != self._last_status:
            self._last_status = status
            self.transfer_status_changed.emit(status)
    
    @staticmethod
    def _format_speed(speed: float) -> str:
        if speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        else:
            return f"{speed / (1024 * 1024 * 1024):.1f} GB/s"
    
    def is_monitoring(self) -> bool:
        return self._monitoring
    
    def get_last_status(self) -> str:
        return self._last_status