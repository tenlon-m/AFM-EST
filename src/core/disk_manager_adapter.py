from typing import List, Optional, Tuple

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .platform_detector import platform_detector
from core.logger import logger
from models.disk_info import DiskInfo, DriveType


class DiskManagerAdapter:
    def __init__(self):
        self._detector = platform_detector
    
    def get_disk_list(self) -> List[DiskInfo]:
        if not HAS_PSUTIL:
            return []
        
        disks = []
        
        try:
            partitions = psutil.disk_partitions(all=False)
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    drive_type = self._determine_drive_type(partition)
                    display_name = self._get_display_name(partition)
                    
                    disk_info = DiskInfo(
                        drive_letter=partition.mountpoint.rstrip('\\'),
                        display_name=display_name,
                        drive_type=drive_type,
                        total_space=usage.total,
                        used_space=usage.used,
                        free_space=usage.free,
                        file_system=partition.fstype,
                    )
                    
                    disks.append(disk_info)
                
                except (PermissionError, OSError) as e:
                    continue
        
        except Exception as e:
            logger.warning(f"获取磁盘信息失败: {e}")
        
        return disks
    
    def _determine_drive_type(self, partition) -> DriveType:
        opts = partition.opts.lower()
        
        if 'cdrom' in opts:
            return DriveType.CDROM
        
        if 'removable' in opts:
            return DriveType.REMOVABLE
        
        if 'network' in opts:
            return DriveType.NETWORK
        
        if 'ram' in opts:
            return DriveType.RAM
        
        if self._detector.is_windows():
            try:
                import ctypes
                drive = partition.mountpoint
                if len(drive) == 3 and drive[1] == ':':
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    type_map = {
                        1: DriveType.REMOVABLE,
                        2: DriveType.REMOVABLE,
                        3: DriveType.FIXED,
                        4: DriveType.NETWORK,
                        5: DriveType.CDROM,
                        6: DriveType.RAM,
                    }
                    return type_map.get(drive_type, DriveType.UNKNOWN)
            except Exception as e:
                logger.debug(f"获取驱动器类型失败: {e}")
        
        else:
            device = partition.device.lower()
            if device.startswith('/dev/sd') or device.startswith('/dev/nvme') or device.startswith('/dev/hd'):
                return DriveType.FIXED
            if device.startswith('/dev/sr'):
                return DriveType.CDROM
            if 'nfs' in partition.fstype.lower() or 'smb' in partition.fstype.lower():
                return DriveType.NETWORK
        
        return DriveType.FIXED
    
    def _get_display_name(self, partition) -> str:
        mountpoint = partition.mountpoint
        
        if self._detector.is_windows():
            if len(mountpoint) == 3 and mountpoint[1] == ':':
                drive_letter = mountpoint[0]
                try:
                    import ctypes
                    volume_name = ctypes.create_unicode_buffer(1024)
                    ctypes.windll.kernel32.GetVolumeInformationW(
                        ctypes.c_wchar_p(mountpoint),
                        volume_name,
                        ctypes.sizeof(volume_name),
                        None, None, None, None
                    )
                    if volume_name.value:
                        return f"{volume_name.value} ({drive_letter}:)"
                except Exception as e:
                    logger.debug(f"获取卷标失败: {e}")
                return f"本地磁盘 ({drive_letter}:)"
        
        else:
            if mountpoint == '/':
                return "根目录 (/)"
            elif mountpoint == '/home':
                return "用户目录 (/home)"
            elif mountpoint.startswith('/mnt/') or mountpoint.startswith('/media/'):
                return f"{mountpoint}"
            else:
                return mountpoint
        
        return mountpoint
    
    def get_disk_usage(self, path: str) -> Optional[Tuple[int, int, int]]:
        if not HAS_PSUTIL:
            return None
        
        try:
            usage = psutil.disk_usage(path)
            return (usage.total, usage.used, usage.free)
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return None
    
    def get_disk_by_mountpoint(self, mountpoint: str) -> Optional[DiskInfo]:
        drive_letter = mountpoint.rstrip('\\')
        disks = self.get_disk_list()
        for disk in disks:
            if disk.drive_letter == drive_letter:
                return disk
        return None
    
    def get_total_disk_space(self) -> Tuple[int, int, int]:
        disks = self.get_disk_list()
        total = sum(d.total_space for d in disks)
        used = sum(d.used_space for d in disks)
        free = sum(d.free_space for d in disks)
        return (total, used, free)


disk_manager_adapter = DiskManagerAdapter()