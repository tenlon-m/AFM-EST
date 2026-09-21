from typing import Optional, List, Dict
from abc import ABC, abstractmethod

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger


class CloudStorageBase(ABC):
    @property
    @abstractmethod
    def service_name(self) -> str:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    def list_directory(self, path: str = "/", **kwargs) -> List[Dict]:
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> bool:
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str, **kwargs) -> bool:
        pass
    
    @abstractmethod
    def create_directory(self, path: str, **kwargs) -> bool:
        pass
    
    @abstractmethod
    def delete(self, paths: List[str], **kwargs) -> bool:
        pass
    
    def get_user_info(self) -> Optional[Dict]:
        return None
    
    def get_service_info(self) -> Dict:
        return {
            'service_name': self.service_name,
            'connected': self.is_connected()
        }
    
    def move(self, src_path: str, dst_path: str, **kwargs) -> bool:
        logger.warning(f"{self.service_name}不支持移动操作")
        return False
    
    def copy(self, src_path: str, dst_path: str, **kwargs) -> bool:
        logger.warning(f"{self.service_name}不支持复制操作")
        return False
    
    def search(self, keyword: str, **kwargs) -> List[Dict]:
        logger.warning(f"{self.service_name}不支持搜索操作")
        return []
    
    def get_quota(self) -> Optional[Dict]:
        return None