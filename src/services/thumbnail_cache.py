from typing import Dict, Optional, Tuple
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timedelta
import threading
import hashlib

from core.logger import logger

from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize

try:
    from core.config import config_manager
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


class MemoryAwareCache:
    DEFAULT_MAX_MEMORY = 100 * 1024 * 1024
    
    def __init__(self, max_memory: int = DEFAULT_MAX_MEMORY):
        self._max_memory = max_memory
        self._current_memory = 0
        self._cache: OrderedDict[str, Tuple[QPixmap, datetime, int]] = OrderedDict()
        self._lock = threading.Lock()
    
    def _calculate_pixmap_memory(self, pixmap: QPixmap) -> int:
        return pixmap.width() * pixmap.height() * 4
    
    def get(self, key: str) -> Optional[Tuple[QPixmap, datetime]]:
        with self._lock:
            if key not in self._cache:
                return None
            
            pixmap, timestamp, memory = self._cache[key]
            self._cache.move_to_end(key)
            return (pixmap, timestamp)
    
    def put(self, key: str, pixmap: QPixmap, timestamp: datetime) -> None:
        memory = self._calculate_pixmap_memory(pixmap)
        
        with self._lock:
            if key in self._cache:
                _, _, old_memory = self._cache[key]
                self._current_memory -= old_memory
                del self._cache[key]
            
            while self._current_memory + memory > self._max_memory and self._cache:
                oldest_key, (_, _, oldest_memory) = self._cache.popitem(last=False)
                self._current_memory -= oldest_memory
            
            self._cache[key] = (pixmap, timestamp, memory)
            self._current_memory += memory
    
    def remove(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                _, _, memory = self._cache[key]
                del self._cache[key]
                self._current_memory -= memory
                return True
            return False
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
    
    def get_memory_usage(self) -> int:
        return self._current_memory


class ThumbnailCache:
    DEFAULT_MAX_SIZE = 100
    DEFAULT_TTL = 3600
    DEFAULT_MAX_MEMORY = 100 * 1024 * 1024
    
    def __init__(self, max_size: int = None, ttl_seconds: int = DEFAULT_TTL, max_memory: int = None):
        # 从配置文件读取参数
        if HAS_CONFIG:
            if max_size is None:
                max_size = config_manager.get("performance.max_cache_items", self.DEFAULT_MAX_SIZE)
            if max_memory is None:
                max_memory_mb = config_manager.get("performance.thumbnail_cache_size_mb", None)
                if max_memory_mb is None:
                    max_memory_mb = self._calculate_optimal_cache_size()
                max_memory = max_memory_mb * 1024 * 1024
        else:
            if max_size is None:
                max_size = self.DEFAULT_MAX_SIZE
            if max_memory is None:
                max_memory = self.DEFAULT_MAX_MEMORY
        
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._max_memory = max_memory
        self._cache: OrderedDict[str, Tuple[QPixmap, datetime]] = OrderedDict()
        self._lock = threading.Lock()
        
        self._current_memory = 0
        self._hit_count = 0
        self._miss_count = 0
    
    @staticmethod
    def _calculate_optimal_cache_size() -> int:
        """根据系统内存计算最优缓存大小（MB）"""
        try:
            import psutil
            total_memory_gb = psutil.virtual_memory().total / (1024 ** 3)
            
            if total_memory_gb >= 32:
                return 500
            elif total_memory_gb >= 16:
                return 300
            elif total_memory_gb >= 8:
                return 150
            elif total_memory_gb >= 4:
                return 100
            else:
                return 50
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return 100
    
    def adjust_cache_size_dynamically(self) -> None:
        """动态调整缓存大小"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_percent = memory.available / memory.total
            
            if available_percent < 0.1:
                new_max_memory = int(self._max_memory * 0.5)
                logger.info(f"内存不足，缓存大小调整为: {new_max_memory / (1024**2):.1f}MB")
            elif available_percent < 0.2:
                new_max_memory = int(self._max_memory * 0.75)
                logger.info(f"内存紧张，缓存大小调整为: {new_max_memory / (1024**2):.1f}MB")
            elif available_percent > 0.5:
                new_max_memory = int(self._max_memory * 1.25)
                logger.info(f"内存充足，缓存大小调整为: {new_max_memory / (1024**2):.1f}MB")
            else:
                return
            
            with self._lock:
                self._max_memory = new_max_memory
                
                while self._current_memory > self._max_memory and self._cache:
                    oldest_key, (oldest_pixmap, _) = self._cache.popitem(last=False)
                    self._current_memory -= oldest_pixmap.width() * oldest_pixmap.height() * 4
                    
        except Exception as e:
            logger.warning(f"动态调整缓存大小失败: {e}")
    
    def get(self, path: str, size: QSize) -> Optional[QPixmap]:
        key = self._make_key(path, size)
        
        with self._lock:
            if key not in self._cache:
                self._miss_count += 1
                return None
            
            pixmap, timestamp = self._cache[key]
            
            if self._is_expired(timestamp):
                del self._cache[key]
                self._current_memory -= self._calculate_pixmap_memory(pixmap)
                self._miss_count += 1
                return None
            
            self._cache.move_to_end(key)
            self._hit_count += 1
            return pixmap
    
    def _calculate_pixmap_memory(self, pixmap: QPixmap) -> int:
        return pixmap.width() * pixmap.height() * 4
    
    def put(self, path: str, size: QSize, pixmap: QPixmap) -> None:
        key = self._make_key(path, size)
        pixmap_memory = self._calculate_pixmap_memory(pixmap)
        
        with self._lock:
            if key in self._cache:
                old_pixmap, _ = self._cache[key]
                self._current_memory -= self._calculate_pixmap_memory(old_pixmap)
                del self._cache[key]
            
            while (len(self._cache) >= self._max_size or 
                   self._current_memory + pixmap_memory > self._max_memory) and self._cache:
                oldest_key, (oldest_pixmap, _) = self._cache.popitem(last=False)
                self._current_memory -= self._calculate_pixmap_memory(oldest_pixmap)
            
            self._cache[key] = (pixmap, datetime.now())
            self._current_memory += pixmap_memory
    
    def contains(self, path: str, size: QSize) -> bool:
        key = self._make_key(path, size)
        
        with self._lock:
            if key not in self._cache:
                return False
            
            _, timestamp = self._cache[key]
            return not self._is_expired(timestamp)
    
    def remove(self, path: str, size: Optional[QSize] = None) -> bool:
        with self._lock:
            if size:
                key = self._make_key(path, size)
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False
            else:
                keys_to_remove = [
                    k for k in self._cache.keys()
                    if k.startswith(f"{path}_")
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                return len(keys_to_remove) > 0
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        with self._lock:
            expired_keys = [
                k for k, (_, timestamp) in self._cache.items()
                if self._is_expired(timestamp)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def _make_key(self, path: str, size: QSize) -> str:
        return f"{path}_{size.width()}x{size.height()}"
    
    def _is_expired(self, timestamp: datetime) -> bool:
        elapsed = datetime.now() - timestamp
        return elapsed.total_seconds() > self._ttl
    
    def size(self) -> int:
        with self._lock:
            return len(self._cache)
    
    def set_max_size(self, max_size: int) -> None:
        with self._lock:
            self._max_size = max_size
            
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def set_ttl(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
    
    def get_statistics(self) -> Dict[str, int]:
        with self._lock:
            total = len(self._cache)
            expired = sum(
                1 for _, timestamp in self._cache.values()
                if self._is_expired(timestamp)
            )
            
            total_requests = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total': total,
                'expired': expired,
                'valid': total - expired,
                'max_size': self._max_size,
                'memory_usage': self._current_memory,
                'max_memory': self._max_memory,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
            }
    
    def set_max_memory(self, max_memory: int) -> None:
        with self._lock:
            self._max_memory = max_memory
            
            while self._current_memory > self._max_memory and self._cache:
                oldest_key, (oldest_pixmap, _) = self._cache.popitem(last=False)
                self._current_memory -= self._calculate_pixmap_memory(oldest_pixmap)
    
    def _make_key_with_hash(self, path: str, size: QSize) -> str:
        try:
            stat = Path(path).stat()
            file_info = f"{path}_{stat.st_mtime}_{stat.st_size}"
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            file_info = path
        
        hash_value = hashlib.md5(file_info.encode()).hexdigest()[:8]
        return f"{hash_value}_{size.width()}x{size.height()}"