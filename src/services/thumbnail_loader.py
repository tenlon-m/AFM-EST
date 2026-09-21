from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor
import threading
import heapq
from enum import IntEnum
import time

from PySide6.QtCore import QObject, Signal, QSize, QThread, QTimer
from PySide6.QtGui import QPixmap

from .thumbnail_cache import ThumbnailCache

from core.logger import logger

try:
    from core.config import config_manager
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


class ThumbnailPriority(IntEnum):
    VISIBLE = 0
    BUFFER = 1
    INVISIBLE = 2


class ThumbnailTask:
    def __init__(self, path: str, size: QSize, priority: ThumbnailPriority, timestamp: float):
        self.path = path
        self.size = size
        self.priority = priority
        self.timestamp = timestamp
    
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class ThumbnailTaskScheduler:
    def __init__(self, max_concurrent: int = 10):
        self._max_concurrent = max_concurrent
        self._task_queue: List[ThumbnailTask] = []
        self._active_count = 0
        self._lock = threading.Lock()
    
    def submit(self, path: str, size: QSize, priority: ThumbnailPriority) -> bool:
        with self._lock:
            if self._active_count >= self._max_concurrent:
                task = ThumbnailTask(path, size, priority, time.time())
                heapq.heappush(self._task_queue, task)
                return False
            else:
                self._active_count += 1
                return True
    
    def complete(self) -> Optional[ThumbnailTask]:
        with self._lock:
            self._active_count -= 1
            if self._task_queue:
                task = heapq.heappop(self._task_queue)
                self._active_count += 1
                return task
            return None
    
    def cancel(self, path: str) -> bool:
        with self._lock:
            for i, task in enumerate(self._task_queue):
                if task.path == path:
                    del self._task_queue[i]
                    heapq.heapify(self._task_queue)
                    return True
            return False
    
    def cancel_all(self) -> int:
        with self._lock:
            count = len(self._task_queue)
            self._task_queue.clear()
            return count


class ThumbnailWorker(QThread):
    loaded = Signal(str, QPixmap)
    failed = Signal(str)
    
    def __init__(self, path: str, size: QSize, parent=None):
        super().__init__(parent)
        self._path = path
        self._size = size
        self._cancelled = False
    
    def cancel(self) -> None:
        self._cancelled = True
    
    def run(self):
        if self._cancelled:
            return
        
        try:
            pixmap = self._load_thumbnail(self._path, self._size)
            if self._cancelled:
                return
            
            if pixmap and not pixmap.isNull():
                self.loaded.emit(self._path, pixmap)
            else:
                self.failed.emit(self._path)
        except Exception:
            if not self._cancelled:
                self.failed.emit(self._path)
    
    def _load_thumbnail(self, path: str, size: QSize) -> Optional[QPixmap]:
        from PySide6.QtGui import QImageReader
        
        reader = QImageReader(path)
        if not reader.canRead():
            return None
        
        original_size = reader.size()
        if original_size.isEmpty():
            return None
        
        scaled_size = self._calculate_scaled_size(original_size, size)
        reader.setScaledSize(scaled_size)
        
        image = reader.read()
        if image.isNull():
            return None
        
        return QPixmap.fromImage(image)
    
    def _calculate_scaled_size(self, original: QSize, target: QSize) -> QSize:
        aspect_ratio = original.width() / original.height()
        
        if aspect_ratio > 1:
            width = target.width()
            height = int(width / aspect_ratio)
        else:
            height = target.height()
            width = int(height * aspect_ratio)
        
        return QSize(max(1, width), max(1, height))


class ThumbnailLoader(QObject):
    loaded = Signal(str, QPixmap)
    failed = Signal(str)
    
    MAX_WORKERS = 4
    MAX_CONCURRENT = 10
    TASK_TIMEOUT = 30.0
    
    def __init__(self, cache: Optional[ThumbnailCache] = None, parent=None):
        super().__init__(parent)
        
        # 从配置文件读取最大工作线程数
        if HAS_CONFIG:
            max_workers = config_manager.get("performance.max_worker_threads", self.MAX_WORKERS)
        else:
            max_workers = self.MAX_WORKERS
        
        self._cache = cache or ThumbnailCache()
        self._workers: Dict[str, ThumbnailWorker] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._scheduler = ThumbnailTaskScheduler(max_concurrent=self.MAX_CONCURRENT)
        
        self._timeout_timer = QTimer(self)
        self._timeout_timer.timeout.connect(self._check_timeouts)
        self._timeout_timer.start(5000)
        
        self._task_timestamps: Dict[str, float] = {}
    
    def load_thumbnail_async(self, path: str, size: QSize, priority: ThumbnailPriority = ThumbnailPriority.VISIBLE) -> Optional[QPixmap]:
        cached = self._cache.get(path, size)
        if cached:
            return cached
        
        with self._lock:
            if path in self._workers:
                return None
            
            if not self._scheduler.submit(path, size, priority):
                return None
            
            worker = ThumbnailWorker(path, size, self)
            worker.loaded.connect(self._on_worker_loaded)
            worker.failed.connect(self._on_worker_failed)
            worker.finished.connect(lambda: self._cleanup_worker(path))
            
            self._workers[path] = worker
            self._task_timestamps[path] = time.time()
            worker.start()
        
        return None
    
    def load_thumbnail_sync(self, path: str, size: QSize) -> Optional[QPixmap]:
        cached = self._cache.get(path, size)
        if cached:
            return cached
        
        try:
            from PySide6.QtGui import QImageReader
            
            reader = QImageReader(path)
            if not reader.canRead():
                return None
            
            original_size = reader.size()
            if original_size.isEmpty():
                return None
            
            aspect_ratio = original_size.width() / original_size.height()
            if aspect_ratio > 1:
                width = size.width()
                height = int(width / aspect_ratio)
            else:
                height = size.height()
                width = int(height * aspect_ratio)
            
            scaled_size = QSize(max(1, width), max(1, height))
            reader.setScaledSize(scaled_size)
            
            image = reader.read()
            if image.isNull():
                return None
            
            pixmap = QPixmap.fromImage(image)
            self._cache.put(path, size, pixmap)
            return pixmap
        
        except Exception as e:
            logger.debug(f"加载缩略图失败: {path} - {e}")
            return None
    
    def cancel_loading(self, path: str) -> bool:
        with self._lock:
            if path not in self._workers:
                self._scheduler.cancel(path)
                return False
            
            worker = self._workers[path]
            worker.cancel()
            if worker.isRunning():
                worker.wait(100)
            
            del self._workers[path]
            if path in self._task_timestamps:
                del self._task_timestamps[path]
            
            self._scheduler.cancel(path)
            return True
    
    def cancel_all(self) -> int:
        with self._lock:
            count = 0
            for path, worker in list(self._workers.items()):
                worker.cancel()
                if worker.isRunning():
                    worker.wait(100)
                    count += 1
            
            self._workers.clear()
            self._task_timestamps.clear()
            count += self._scheduler.cancel_all()
            return count
    
    def _check_timeouts(self) -> None:
        current_time = time.time()
        timeout_paths = []
        
        with self._lock:
            for path, timestamp in list(self._task_timestamps.items()):
                if current_time - timestamp > self.TASK_TIMEOUT:
                    timeout_paths.append(path)
        
        for path in timeout_paths:
            self.cancel_loading(path)
    
    def _on_worker_loaded(self, path: str, pixmap: QPixmap):
        worker = self._workers.get(path)
        if worker:
            size = QSize(worker._size.width(), worker._size.height())
            self._cache.put(path, size, pixmap)
        
        self.loaded.emit(path, pixmap)
        
        next_task = self._scheduler.complete()
        if next_task:
            self.load_thumbnail_async(next_task.path, next_task.size, next_task.priority)
    
    def _on_worker_failed(self, path: str):
        self.failed.emit(path)
        self._scheduler.complete()
    
    def _cleanup_worker(self, path: str):
        with self._lock:
            if path in self._workers:
                del self._workers[path]
            if path in self._task_timestamps:
                del self._task_timestamps[path]
    
    def get_cache_statistics(self) -> Dict[str, int]:
        return self._cache.get_statistics()
    
    def clear_cache(self) -> None:
        self._cache.clear()
    
    def cleanup_cache(self) -> int:
        return self._cache.cleanup_expired()
    
    def shutdown(self) -> None:
        self.cancel_all()
        self._executor.shutdown(wait=True)