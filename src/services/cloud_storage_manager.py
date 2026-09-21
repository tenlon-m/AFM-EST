from typing import Optional, List, Dict
from enum import Enum

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class CloudStorageType(Enum):
    WEBDAV = "webdav"
    BAIDU = "baidu"
    ALIYUN = "aliyun"



class UnifiedCloudStorageManager:
    def __init__(self):
        self._services: Dict[CloudStorageType, any] = {}
        self._current_service: Optional[CloudStorageType] = None
        
        self._init_services()
    
    def _init_services(self):
        try:
            from services.webdav_service import webdav_service
            self._services[CloudStorageType.WEBDAV] = webdav_service
        except Exception as e:
            logger.debug(f"WebDAV服务未加载: {e}")
        
        try:
            from services.baidu_pan_service import baidu_pan_service
            self._services[CloudStorageType.BAIDU] = baidu_pan_service
        except Exception as e:
            logger.debug(f"百度网盘服务未加载: {e}")
        
        try:
            from services.aliyun_pan_service import aliyun_pan_service
            self._services[CloudStorageType.ALIYUN] = aliyun_pan_service
        except Exception as e:
            logger.debug(f"阿里云盘服务未加载: {e}")
        
        logger.info(f"云存储管理器已初始化，支持: {list(self._services.keys())}")
    
    def get_available_services(self) -> List[CloudStorageType]:
        return list(self._services.keys())
    
    def set_current_service(self, service_type: CloudStorageType) -> bool:
        if service_type not in self._services:
            logger.error(f"不支持的云存储类型: {service_type}")
            return False
        
        self._current_service = service_type
        logger.info(f"切换到云存储服务: {service_type.value}")
        return True
    
    def get_current_service(self) -> Optional[CloudStorageType]:
        return self._current_service
    
    def is_connected(self, service_type: CloudStorageType = None) -> bool:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            return False
        
        service = self._services[service_type]
        return service.is_connected()
    
    def list_directory(self, path: str = "/", service_type: CloudStorageType = None, **kwargs) -> List[Dict]:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            logger.error("未指定云存储服务")
            return []
        
        service = self._services[service_type]
        
        try:
            if service_type == CloudStorageType.BAIDU:
                return service.list_directory(remote_path=path)
            elif service_type == CloudStorageType.ALIYUN:
                parent_file_id = kwargs.get('parent_file_id', 'root')
                return service.list_directory(parent_file_id=parent_file_id)
            elif service_type == CloudStorageType.WEBDAV:
                return service.list_directory(remote_path=path)
            else:
                return []
        except Exception as e:
            logger.error(f"列出目录失败: {e}")
            return []
    
    def upload_file(self, local_path: str, remote_path: str, service_type: CloudStorageType = None, **kwargs) -> bool:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            logger.error("未指定云存储服务")
            return False
        
        service = self._services[service_type]
        
        try:
            if service_type == CloudStorageType.BAIDU:
                return service.upload_file(local_path=local_path, remote_path=remote_path)
            elif service_type == CloudStorageType.ALIYUN:
                parent_file_id = kwargs.get('parent_file_id', 'root')
                return service.upload_file(local_path=local_path, parent_file_id=parent_file_id)
            elif service_type == CloudStorageType.WEBDAV:
                return service.upload_file(local_path=local_path, remote_path=remote_path)
            else:
                return False
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str, service_type: CloudStorageType = None, **kwargs) -> bool:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            logger.error("未指定云存储服务")
            return False
        
        service = self._services[service_type]
        
        try:
            if service_type == CloudStorageType.BAIDU:
                return service.download_file(remote_path=remote_path, local_path=local_path)
            elif service_type == CloudStorageType.ALIYUN:
                file_id = kwargs.get('file_id', '')
                return service.download_file(file_id=file_id, local_path=local_path)
            elif service_type == CloudStorageType.WEBDAV:
                return service.download_file(remote_path=remote_path, local_path=local_path)
            else:
                return False
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False
    
    def create_directory(self, path: str, service_type: CloudStorageType = None, **kwargs) -> bool:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            logger.error("未指定云存储服务")
            return False
        
        service = self._services[service_type]
        
        try:
            if service_type == CloudStorageType.BAIDU:
                return service.create_directory(remote_path=path)
            elif service_type == CloudStorageType.ALIYUN:
                parent_file_id = kwargs.get('parent_file_id', 'root')
                name = kwargs.get('name', path)
                return service.create_directory(name=name, parent_file_id=parent_file_id)
            elif service_type == CloudStorageType.WEBDAV:
                return service.create_directory(remote_path=path)
            else:
                return False
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False
    
    def delete(self, paths: List[str], service_type: CloudStorageType = None, **kwargs) -> bool:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            logger.error("未指定云存储服务")
            return False
        
        service = self._services[service_type]
        
        try:
            if service_type == CloudStorageType.BAIDU:
                return service.delete(remote_paths=paths)
            elif service_type == CloudStorageType.ALIYUN:
                file_ids = kwargs.get('file_ids', paths)
                return service.delete(file_ids=file_ids)
            elif service_type == CloudStorageType.WEBDAV:
                for path in paths:
                    if not service.delete(remote_path=path):
                        return False
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    def get_service_info(self, service_type: CloudStorageType = None) -> Dict:
        if service_type is None:
            service_type = self._current_service
        
        if service_type is None or service_type not in self._services:
            return {}
        
        service = self._services[service_type]
        
        info = {
            'type': service_type.value,
            'connected': service.is_connected()
        }
        
        try:
            if hasattr(service, 'get_user_info'):
                user_info = service.get_user_info()
                if user_info:
                    info.update(user_info)
            
            if hasattr(service, 'get_server_info'):
                server_info = service.get_server_info()
                if server_info:
                    info.update(server_info)
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        
        return info


cloud_storage_manager = UnifiedCloudStorageManager()