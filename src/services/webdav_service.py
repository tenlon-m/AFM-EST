from typing import Optional, List, Dict

import os

try:
    from webdav3.client import Client
    HAS_WEBDAV = True
except ImportError:
    HAS_WEBDAV = False

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger

from services.cloud_storage_base import CloudStorageBase


class WebDAVService(CloudStorageBase):
    @property
    def service_name(self) -> str:
        return "WebDAV"
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._connected = False
        self._server_url = ""
        self._username = ""
        self._root_path = "/"
        
        if not HAS_WEBDAV:
            logger.warning("webdavclient3库未安装，WebDAV功能不可用")
    
    def connect(self, server_url: str, username: str = "", password: str = "", root_path: str = "/") -> bool:
        if not HAS_WEBDAV:
            logger.error("webdavclient3库未安装")
            return False
        
        try:
            options = {
                'webdav_hostname': server_url,
                'webdav_root': root_path,
            }
            
            if username:
                options['webdav_login'] = username
            if password:
                options['webdav_password'] = password
            
            self._client = Client(options)
            
            if self._client.check():
                self._connected = True
                self._server_url = server_url
                self._username = username
                self._root_path = root_path
                
                logger.info(f"WebDAV连接成功: {server_url}")
                return True
            else:
                logger.error(f"WebDAV连接失败: {server_url}")
                return False
                
        except Exception as e:
            logger.error(f"WebDAV连接异常: {e}")
            return False
    
    def disconnect(self) -> None:
        self._client = None
        self._connected = False
        self._server_url = ""
        self._username = ""
        logger.info("WebDAV已断开连接")
    
    def is_connected(self) -> bool:
        return self._connected and self._client is not None
    
    def list_directory(self, remote_path: str = "/") -> List[Dict]:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return []
        
        try:
            items = self._client.list(remote_path)
            
            result = []
            for item in items:
                if item == remote_path:
                    continue
                
                is_dir = self._client.is_dir(item)
                name = os.path.basename(item.rstrip('/'))
                
                info = {
                    'path': item,
                    'name': name,
                    'is_dir': is_dir,
                    'size': 0,
                    'modified': ''
                }
                
                try:
                    if not is_dir:
                        info_data = self._client.info(item)
                        info['size'] = int(info_data.get('size', 0))
                        info['modified'] = info_data.get('modified', '')
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                
                result.append(info)
            
            return result
            
        except Exception as e:
            logger.error(f"列出目录失败: {e}")
            return []
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self._client.download_sync(remote_path=remote_path, local_path=local_path)
            
            logger.info(f"下载成功: {remote_path} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            if not os.path.exists(local_path):
                logger.error(f"本地文件不存在: {local_path}")
                return False
            
            self._client.upload_sync(remote_path=remote_path, local_path=local_path)
            
            logger.info(f"上传成功: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"上传失败: {e}")
            return False
    
    def create_directory(self, remote_path: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            self._client.mkdir(remote_path)
            logger.info(f"创建目录成功: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False
    
    def delete(self, remote_path: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            self._client.clean(remote_path)
            logger.info(f"删除成功: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    def move(self, remote_src: str, remote_dst: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            self._client.move(remote_src, remote_dst)
            logger.info(f"移动成功: {remote_src} -> {remote_dst}")
            return True
            
        except Exception as e:
            logger.error(f"移动失败: {e}")
            return False
    
    def copy(self, remote_src: str, remote_dst: str) -> bool:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return False
        
        try:
            self._client.copy(remote_src, remote_dst)
            logger.info(f"复制成功: {remote_src} -> {remote_dst}")
            return True
            
        except Exception as e:
            logger.error(f"复制失败: {e}")
            return False
    
    def get_info(self, remote_path: str) -> Optional[Dict]:
        if not self.is_connected():
            logger.error("WebDAV未连接")
            return None
        
        try:
            info = self._client.info(remote_path)
            return {
                'path': remote_path,
                'size': int(info.get('size', 0)),
                'modified': info.get('modified', ''),
                'created': info.get('created', ''),
                'is_dir': self._client.is_dir(remote_path)
            }
            
        except Exception as e:
            logger.error(f"获取信息失败: {e}")
            return None
    
    def get_server_info(self) -> Dict:
        return {
            'connected': self._connected,
            'server_url': self._server_url,
            'username': self._username,
            'root_path': self._root_path
        }


webdav_service = WebDAVService()