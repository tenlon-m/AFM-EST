try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import List, Optional
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QThread

from models.disk_info import DiskInfo, DriveType
from core.logger import logger as _logger


class DiskInfoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = _logger
    
    def run(self):
        if not HAS_PSUTIL:
            self.error.emit("psutil库未安装，无法获取磁盘信息")
            return
        try:
            disks = self._get_disk_info()
            self.finished.emit(disks)
        except Exception as e:
            self._logger.error(f"Failed to get disk info: {e}")
            self.error.emit(str(e))
    
    def _get_disk_info(self) -> List[DiskInfo]:
        disks = []
        
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                drive_type = self._determine_drive_type(partition)
                
                display_name = self._get_display_name(partition)
                
                disk_info = DiskInfo(
                    drive_letter=partition.mountpoint,
                    display_name=display_name,
                    drive_type=drive_type,
                    total_space=usage.total,
                    used_space=usage.used,
                    free_space=usage.free,
                    file_system=partition.fstype,
                    is_ready=True,
                )
                
                disks.append(disk_info)
            
            except (PermissionError, OSError) as e:
                self._logger.warning(f"Cannot access disk {partition.mountpoint}: {e}")
                continue
        
        return disks
    
    def _determine_drive_type(self, partition) -> DriveType:
        opts = partition.opts.lower()
        
        if 'cdrom' in opts:
            return DriveType.CDROM
        elif 'removable' in opts:
            return DriveType.REMOVABLE
        elif 'network' in opts or '//' in partition.mountpoint:
            return DriveType.NETWORK
        elif 'ram' in opts:
            return DriveType.RAM
        else:
            return DriveType.FIXED
    
    def _get_display_name(self, partition) -> str:
        mountpoint = partition.mountpoint
        
        if len(mountpoint) == 3 and mountpoint[1] == ':':
            drive_letter = mountpoint[0]
            try:
                import win32api
                import win32file
                volume_name = win32api.GetVolumeInformation(mountpoint)[0]
                if volume_name:
                    return f"{volume_name} ({drive_letter}:)"
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            return f"本地磁盘 ({drive_letter}:)"
        
        return mountpoint


class DiskInfoProvider(QObject):
    disks_loaded = Signal(list)
    load_error = Signal(str)
    
    CACHE_TTL = 5
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._logger = _logger
        self._cache: Optional[List[DiskInfo]] = None
        self._cache_time: Optional[datetime] = None
        self._worker: Optional[DiskInfoWorker] = None
    
    def get_disk_info(self, use_cache: bool = True) -> List[DiskInfo]:
        if use_cache and self._is_cache_valid():
            return self._cache or []
        
        return self._fetch_disk_info_sync()
    
    def get_disk_info_async(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        
        self._worker = DiskInfoWorker(self)
        self._worker.finished.connect(self._on_disks_loaded)
        self._worker.error.connect(self._on_load_error)
        self._worker.start()
    
    def _on_disks_loaded(self, disks: List[DiskInfo]) -> None:
        self._cache = disks
        self._cache_time = datetime.now()
        self.disks_loaded.emit(disks)
    
    def _on_load_error(self, error: str) -> None:
        self.load_error.emit(error)
    
    def _is_cache_valid(self) -> bool:
        if self._cache is None or self._cache_time is None:
            return False
        
        elapsed = datetime.now() - self._cache_time
        return elapsed.total_seconds() < self.CACHE_TTL
    
    def _fetch_disk_info_sync(self) -> List[DiskInfo]:
        disks = []
        
        if not HAS_PSUTIL:
            return disks
        
        try:
            for partition in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    drive_type = self._determine_drive_type(partition)
                    display_name = self._get_display_name(partition)
                    
                    disk_info = DiskInfo(
                        drive_letter=partition.mountpoint,
                        display_name=display_name,
                        drive_type=drive_type,
                        total_space=usage.total,
                        used_space=usage.used,
                        free_space=usage.free,
                        file_system=partition.fstype,
                        is_ready=True,
                    )
                    
                    disks.append(disk_info)
                
                except (PermissionError, OSError) as e:
                    self._logger.warning(f"无法访问磁盘 {partition.mountpoint}: {e}")
                    continue
        
        except Exception as e:
            self._logger.error(f"获取磁盘信息失败: {e}", exc_info=True)
        
        self._cache = disks
        self._cache_time = datetime.now()
        
        return disks
    
    def _determine_drive_type(self, partition) -> DriveType:
        opts = partition.opts.lower()
        
        if 'cdrom' in opts:
            return DriveType.CDROM
        elif 'removable' in opts:
            return DriveType.REMOVABLE
        elif 'network' in opts or '//' in partition.mountpoint:
            return DriveType.NETWORK
        elif 'ram' in opts:
            return DriveType.RAM
        else:
            return DriveType.FIXED
    
    def _get_display_name(self, partition) -> str:
        mountpoint = partition.mountpoint
        
        if len(mountpoint) == 3 and mountpoint[1] == ':':
            drive_letter = mountpoint[0]
            try:
                import win32api
                volume_name = win32api.GetVolumeInformation(mountpoint)[0]
                if volume_name:
                    return f"{volume_name} ({drive_letter}:)"
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            return f"本地磁盘 ({drive_letter}:)"
        
        return mountpoint
    
    def invalidate_cache(self) -> None:
        self._cache = None
        self._cache_time = None