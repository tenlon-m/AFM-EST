from typing import Optional, List, Dict
import os
import json
import time
import base64
import hashlib
import urllib.parse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from core.logger import logger as _logger
except ImportError:
    from core.logger import null_logger as _logger

logger = _logger

from services.cloud_storage_base import CloudStorageBase


class AliyunPanService(CloudStorageBase):
    API_BASE = "https://api.aliyundrive.com"
    PASSPORT_API = "https://passport.aliyundrive.com"
    
    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: int = 0
        self._user_id: str = ""
        self._connected = False
        
        if not HAS_REQUESTS:
            logger.warning("requests库未安装，阿里云盘功能不可用")
    
    @property
    def service_name(self) -> str:
        return "阿里云盘"
    
    def get_qrcode_login_url(self) -> Dict:
        try:
            url = f"{self.PASSPORT_API}/v2/login/qrcode/init"
            response = requests.post(url, json={})
            data = response.json()
            
            if 'data' in data:
                return {
                    'qrcode_url': data['data']['qrcodeUrl'],
                    'sid': data['data']['sid'],
                    't': data['data']['t']
                }
            return {}
            
        except Exception as e:
            logger.error(f"获取二维码失败: {e}")
            return {}
    
    def check_qrcode_status(self, sid: str, t: str) -> Dict:
        try:
            url = f"{self.PASSPORT_API}/v2/login/qrcode/query"
            params = {'sid': sid, 't': t}
            response = requests.get(url, params=params)
            data = response.json()
            
            status = data.get('data', {}).get('status', '')
            
            if status == 'LOGIN_SUCCESS':
                self._access_token = data['data'].get('accessToken', '')
                self._refresh_token = data['data'].get('refreshToken', '')
                self._expires_at = int(time.time()) + data['data'].get('expireTime', 7200)
                self._connected = True
                
                logger.info("阿里云盘扫码登录成功")
                return {'status': 'success', 'message': '登录成功'}
            
            elif status == 'WAITING':
                return {'status': 'waiting', 'message': '等待扫码'}
            
            elif status == 'EXPIRED':
                return {'status': 'expired', 'message': '二维码已过期'}
            
            else:
                return {'status': 'unknown', 'message': f'未知状态: {status}'}
                
        except Exception as e:
            logger.error(f"检查二维码状态失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 7200) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = int(time.time()) + expires_in
        self._connected = True
        logger.info("阿里云盘已设置访问令牌")
    
    def refresh_access_token(self) -> bool:
        if not self._refresh_token:
            logger.error("无刷新令牌")
            return False
        
        try:
            url = f"{self.PASSPORT_API}/v2/account/token"
            data = {
                'refresh_token': self._refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if 'access_token' in result:
                self._access_token = result['access_token']
                self._refresh_token = result.get('refresh_token', self._refresh_token)
                self._expires_at = int(time.time()) + result.get('expire_time', 7200)
                
                logger.info("阿里云盘令牌刷新成功")
                return True
            else:
                logger.error("阿里云盘令牌刷新失败")
                return False
                
        except Exception as e:
            logger.error(f"阿里云盘令牌刷新异常: {e}")
            return False
    
    def is_connected(self) -> bool:
        if not self._connected or not self._access_token:
            return False
        
        if time.time() >= self._expires_at - 300:
            if self._refresh_token:
                return self.refresh_access_token()
            return False
        
        return True
    
    def _api_request(self, uri: str, method: str = "POST", data: dict = None) -> Optional[dict]:
        if not self.is_connected():
            logger.error("阿里云盘未连接")
            return None
        
        url = f"{self.API_BASE}{uri}"
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers, json=data)
            
            return response.json()
            
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return None
    
    def get_user_info(self) -> Optional[Dict]:
        result = self._api_request('/v2/user/get')
        
        if result and 'user_id' in result:
            self._user_id = result['user_id']
            return {
                'user_id': result.get('user_id', ''),
                'nick_name': result.get('nick_name', ''),
                'avatar': result.get('avatar', ''),
                'default_drive_id': result.get('default_drive_id', '')
            }
        return None
    
    def list_directory(self, path: str = "/", **kwargs) -> List[Dict]:
        parent_file_id = kwargs.get('parent_file_id', path if path != "/" else "root")
        drive_id = kwargs.get('drive_id', None)
        if drive_id is None:
            user_info = self.get_user_info()
            if user_info:
                drive_id = user_info.get('default_drive_id', '')
            else:
                return []
        
        data = {
            'drive_id': drive_id,
            'parent_file_id': parent_file_id,
            'limit': 100,
            'order_by': 'name',
            'order_direction': 'ASC'
        }
        
        result = self._api_request('/v2/file/list', data=data)
        
        if not result or 'items' not in result:
            return []
        
        items = []
        for item in result['items']:
            items.append({
                'file_id': item['file_id'],
                'name': item['name'],
                'is_dir': item['type'] == 'folder',
                'size': item.get('size', 0),
                'modified': item.get('updated_at', ''),
                'drive_id': item.get('drive_id', drive_id)
            })
        
        return items
    
    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> bool:
        if not self.is_connected():
            logger.error("阿里云盘未连接")
            return False
        
        if not os.path.exists(local_path):
            logger.error(f"本地文件不存在: {local_path}")
            return False
        
        try:
            parent_file_id = kwargs.get('parent_file_id', remote_path if remote_path != "/" else "root")
            drive_id = kwargs.get('drive_id', None)
            file_name = os.path.basename(local_path)
            try:
                file_size = os.path.getsize(local_path)
            except (OSError, PermissionError):
                file_size = 0
            
            with open(local_path, 'rb') as f:
                sha1_hash = hashlib.sha1()
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sha1_hash.update(chunk)
                content_sha1 = sha1_hash.hexdigest()
                f.seek(0)
            sha1 = content_sha1
            
            if drive_id is None:
                user_info = self.get_user_info()
                if user_info:
                    drive_id = user_info.get('default_drive_id', '')
                else:
                    return False
            
            data = {
                'drive_id': drive_id,
                'parent_file_id': parent_file_id,
                'name': file_name,
                'type': 'file',
                'check_name_mode': 'refuse',
                'size': file_size,
                'content_hash': sha1,
                'content_hash_name': 'sha1'
            }
            
            result = self._api_request('/v2/file/create', data=data)
            
            if result and 'file_id' in result:
                upload_type = result.get('upload_type', '')
                
                if upload_type == 'UPLOAD_TYPE_READY':
                    logger.info(f"文件秒传成功: {file_name}")
                    return True
                
                elif upload_type == 'UPLOAD_TYPE_URL':
                    upload_url = result.get('upload_url', '')
                    
                    with open(local_path, 'rb') as f:
                        response = requests.put(upload_url, data=f)
                    
                    if response.status_code == 200:
                        logger.info(f"上传成功: {file_name}")
                        return True
                    else:
                        logger.error(f"上传失败: {response.status_code}")
                        return False
            
            return False
            
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str, **kwargs) -> bool:
        file_id = kwargs.get('file_id', remote_path)
        drive_id = kwargs.get('drive_id', None)
        if not self.is_connected():
            logger.error("阿里云盘未连接")
            return False
        
        if drive_id is None:
            user_info = self.get_user_info()
            if user_info:
                drive_id = user_info.get('default_drive_id', '')
            else:
                return False
        
        data = {
            'drive_id': drive_id,
            'file_id': file_id
        }
        
        result = self._api_request('/v2/file/get_download_url', data=data)
        
        if not result or 'url' not in result:
            logger.error("获取下载链接失败")
            return False
        
        try:
            download_url = result['url']
            response = requests.get(download_url, stream=True)
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"下载成功: {file_id} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False
    
    def create_directory(self, path: str, **kwargs) -> bool:
        name = kwargs.get('name', os.path.basename(path.rstrip('/')) if '/' in path else path)
        parent_file_id = kwargs.get('parent_file_id', "root")
        drive_id = kwargs.get('drive_id', None)
        if drive_id is None:
            user_info = self.get_user_info()
            if user_info:
                drive_id = user_info.get('default_drive_id', '')
            else:
                return False
        
        data = {
            'drive_id': drive_id,
            'parent_file_id': parent_file_id,
            'name': name,
            'type': 'folder',
            'check_name_mode': 'refuse'
        }
        
        result = self._api_request('/v2/file/create', data=data)
        
        if result and 'file_id' in result:
            logger.info(f"创建目录成功: {name}")
            return True
        return False
    
    def delete(self, paths: List[str], **kwargs) -> bool:
        file_ids = kwargs.get('file_ids', paths)
        drive_id = kwargs.get('drive_id', None)
        if drive_id is None:
            user_info = self.get_user_info()
            if user_info:
                drive_id = user_info.get('default_drive_id', '')
            else:
                return False
        
        data = {
            'drive_id': drive_id,
            'file_ids': file_ids
        }
        
        result = self._api_request('/v2/file/delete', data=data)
        
        if result:
            logger.info(f"删除成功: {file_ids}")
            return True
        return False


aliyun_pan_service = AliyunPanService()