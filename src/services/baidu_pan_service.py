from typing import Optional, List, Dict

import os
import json
import time
import hashlib
import sqlite3



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


class BaiduPanService(CloudStorageBase):
    API_BASE = "https://pan.baidu.com/rest/2.0/xpan"
    
    OAUTH_URL = "https://openapi.baidu.com/oauth/2.0/authorize"
    TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
    
    def __init__(self):
        super().__init__()
        self._resume_db = os.path.join(os.path.expanduser("~"), ".afm_est", "baidu_resume.db")
        self._init_resume_db()
        
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: int = 0
        self._app_key = ""
        self._app_secret = ""
        self._connected = False
        
        if not HAS_REQUESTS:
            logger.warning("requests库未安装，百度网盘功能不可用")
    
    def _init_resume_db(self):
        """初始化断点续传数据库"""
        os.makedirs(os.path.dirname(self._resume_db), exist_ok=True)
        conn = None
        try:
            conn = sqlite3.connect(self._resume_db)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS upload_resume (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_path TEXT NOT NULL,
                    remote_path TEXT NOT NULL,
                    upload_id TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    chunk_size INTEGER NOT NULL,
                    uploaded_chunks TEXT NOT NULL,
                    block_list TEXT NOT NULL,
                    created_time REAL NOT NULL,
                    UNIQUE(local_path, remote_path)
                )
            ''')
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def _save_resume_info(self, local_path: str, remote_path: str, upload_id: str, 
                          file_size: int, chunk_size: int, uploaded_chunks: List[int], 
                          block_list: List[str]):
        """保存断点续传信息"""
        conn = None
        try:
            conn = sqlite3.connect(self._resume_db)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO upload_resume 
                (local_path, remote_path, upload_id, file_size, chunk_size, uploaded_chunks, block_list, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (local_path, remote_path, upload_id, file_size, chunk_size, 
                  json.dumps(uploaded_chunks), json.dumps(block_list), time.time()))
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def _load_resume_info(self, local_path: str, remote_path: str) -> Optional[Dict]:
        """加载断点续传信息"""
        conn = None
        try:
            conn = sqlite3.connect(self._resume_db)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT upload_id, file_size, chunk_size, uploaded_chunks, block_list
                FROM upload_resume
                WHERE local_path = ? AND remote_path = ?
            ''', (local_path, remote_path))
            row = cursor.fetchone()
            
            if row:
                return {
                    'upload_id': row[0],
                    'file_size': row[1],
                    'chunk_size': row[2],
                    'uploaded_chunks': json.loads(row[3]),
                    'block_list': json.loads(row[4])
                }
            return None
        finally:
            if conn:
                conn.close()
    
    def _delete_resume_info(self, local_path: str, remote_path: str):
        """删除断点续传信息"""
        conn = None
        try:
            conn = sqlite3.connect(self._resume_db)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM upload_resume
                WHERE local_path = ? AND remote_path = ?
            ''', (local_path, remote_path))
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    @property
    def service_name(self) -> str:
        return "百度网盘"
    
    def set_app_credentials(self, app_key: str, app_secret: str) -> None:
        self._app_key = app_key
        self._app_secret = app_secret
    
    def get_auth_url(self, redirect_uri: str = "oob") -> str:
        params = {
            'response_type': 'code',
            'client_id': self._app_key,
            'redirect_uri': redirect_uri,
            'scope': 'basic,netdisk'
        }
        
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.OAUTH_URL}?{query}"
    
    def authenticate_with_code(self, auth_code: str, redirect_uri: str = "oob") -> bool:
        if not HAS_REQUESTS:
            logger.error("requests库未安装")
            return False
        
        try:
            params = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': self._app_key,
                'client_secret': self._app_secret,
                'redirect_uri': redirect_uri
            }
            
            response = requests.get(self.TOKEN_URL, params=params)
            data = response.json()
            
            if 'access_token' in data:
                self._access_token = data['access_token']
                self._refresh_token = data.get('refresh_token', '')
                self._expires_at = int(time.time()) + data.get('expires_in', 0)
                self._connected = True
                
                logger.info("百度网盘认证成功")
                return True
            else:
                logger.error(f"百度网盘认证失败: {data.get('error_description', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"百度网盘认证异常: {e}")
            return False
    
    def set_access_token(self, access_token: str, refresh_token: str = "", expires_in: int = 2592000) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = int(time.time()) + expires_in
        self._connected = True
        logger.info("百度网盘已设置访问令牌")
    
    def refresh_access_token(self) -> bool:
        if not self._refresh_token:
            logger.error("无刷新令牌")
            return False
        
        try:
            params = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'client_id': self._app_key,
                'client_secret': self._app_secret
            }
            
            response = requests.get(self.TOKEN_URL, params=params)
            data = response.json()
            
            if 'access_token' in data:
                self._access_token = data['access_token']
                self._refresh_token = data.get('refresh_token', self._refresh_token)
                self._expires_at = int(time.time()) + data.get('expires_in', 0)
                
                logger.info("百度网盘令牌刷新成功")
                return True
            else:
                logger.error("百度网盘令牌刷新失败")
                return False
                
        except Exception as e:
            logger.error(f"百度网盘令牌刷新异常: {e}")
            return False
    
    def is_connected(self) -> bool:
        if not self._connected or not self._access_token:
            return False
        
        if time.time() >= self._expires_at - 300:
            if self._refresh_token:
                return self.refresh_access_token()
            return False
        
        return True
    
    def _api_request(self, uri: str, method: str = "GET", params: dict = None, data: dict = None) -> Optional[dict]:
        if not self.is_connected():
            logger.error("百度网盘未连接")
            return None
        
        url = f"{self.API_BASE}{uri}"
        
        if params is None:
            params = {}
        params['access_token'] = self._access_token
        
        try:
            if method == "GET":
                response = requests.get(url, params=params)
            else:
                response = requests.post(url, params=params, data=data)
            
            result = response.json()
            
            if 'errno' in result and result['errno'] != 0:
                logger.error(f"API错误: {result.get('errmsg', '未知错误')}")
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return None
    
    def list_directory(self, path: str = "/", **kwargs) -> List[Dict]:
        remote_path = kwargs.get('remote_path', path)
        page = kwargs.get('page', 1)
        num = kwargs.get('num', 100)
        params = {
            'method': 'list',
            'dir': remote_path,
            'page': page,
            'num': num,
            'order': 'name',
            'desc': 0
        }
        
        result = self._api_request('/file', params=params)
        
        if not result or 'list' not in result:
            return []
        
        items = []
        for item in result['list']:
            items.append({
                'path': item['path'],
                'name': item['server_filename'],
                'is_dir': item['isdir'] == 1,
                'size': item['size'],
                'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['server_mtime']))
            })
        
        return items
    
    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> bool:
        on_progress = kwargs.get('on_progress', None)
        if not self.is_connected():
            logger.error("百度网盘未连接")
            return False
        
        if not os.path.exists(local_path):
            logger.error(f"本地文件不存在: {local_path}")
            return False
        
        try:
            try:
                file_size = os.path.getsize(local_path)
            except (OSError, PermissionError):
                file_size = 0
            
            if file_size < 2 * 1024 * 1024:
                return self._upload_small_file(local_path, remote_path)
            else:
                return self._upload_large_file(local_path, remote_path, on_progress)
                
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return False
    
    def _upload_small_file(self, local_path: str, remote_path: str) -> bool:
        upload_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=upload&access_token={self._access_token}&path={remote_path}"
        
        with open(local_path, 'rb') as f:
            files = {'file': (os.path.basename(local_path), f)}
            response = requests.post(upload_url, files=files)
        
        result = response.json()
        
        if 'path' in result:
            logger.info(f"上传成功: {remote_path}")
            return True
        else:
            logger.error(f"上传失败: {result}")
            return False
    
    def _upload_large_file(self, local_path: str, remote_path: str, on_progress: callable = None) -> bool:
        try:
            from core.config import config_manager
            chunk_size_mb = config_manager.get("cloud_storage.baidu_chunk_size_mb", 2)
            CHUNK_SIZE = chunk_size_mb * 1024 * 1024
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            CHUNK_SIZE = 2 * 1024 * 1024
        
        try:
            try:
                file_size = os.path.getsize(local_path)
            except (OSError, PermissionError):
                file_size = 0
            block_list = []
            uploaded_chunks = []
            
            # 尝试加载断点续传信息
            resume_info = self._load_resume_info(local_path, remote_path)
            
            if resume_info and resume_info['file_size'] == file_size:
                # 恢复上传
                upload_id = resume_info['upload_id']
                uploaded_chunks = resume_info['uploaded_chunks']
                block_list = resume_info['block_list']
                logger.info(f"恢复上传: {local_path}, 已上传 {len(uploaded_chunks)} 个分片")
            else:
                # 新上传
                precreate_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=precreate"
                params = {
                    'access_token': self._access_token,
                    'path': remote_path,
                    'size': file_size,
                    'isdir': 0,
                    'autoinit': 1
                }
                
                response = requests.post(precreate_url, params=params)
                precreate_result = response.json()
                
                if 'uploadid' not in precreate_result:
                    logger.error(f"预上传失败: {precreate_result}")
                    return False
                
                upload_id = precreate_result['uploadid']
            
            with open(local_path, 'rb') as f:
                chunk_index = 0
                while True:
                    chunk_data = f.read(CHUNK_SIZE)
                    if not chunk_data:
                        break
                    
                    # 跳过已上传的分片
                    if chunk_index in uploaded_chunks:
                        md5 = hashlib.md5(chunk_data).hexdigest()
                        block_list.append(md5)
                        chunk_index += 1
                        continue
                    
                    md5 = hashlib.md5(chunk_data).hexdigest()
                    block_list.append(md5)
                    
                    upload_url = f"https://d.pcs.baidu.com/rest/2.0/pcs/superfile2?method=upload"
                    upload_params = {
                        'access_token': self._access_token,
                        'type': 'tmpfile',
                        'path': remote_path,
                        'uploadid': upload_id,
                        'partseq': chunk_index
                    }
                    
                    files = {'file': (f'chunk_{chunk_index}', chunk_data)}
                    upload_response = requests.post(upload_url, params=upload_params, files=files)
                    
                    if upload_response.status_code != 200:
                        logger.error(f"分片上传失败: chunk_{chunk_index}")
                        # 保存断点信息
                        self._save_resume_info(local_path, remote_path, upload_id, 
                                             file_size, CHUNK_SIZE, uploaded_chunks, block_list)
                        return False
                    
                    uploaded_chunks.append(chunk_index)
                    
                    # 定期保存断点信息（每10个分片）
                    if chunk_index % 10 == 0:
                        self._save_resume_info(local_path, remote_path, upload_id, 
                                             file_size, CHUNK_SIZE, uploaded_chunks, block_list)
                    
                    if on_progress:
                        progress = int((f.tell() / file_size) * 100)
                        on_progress(progress, f.tell(), file_size)
                    
                    chunk_index += 1
            
            create_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=create"
            create_params = {
                'access_token': self._access_token,
                'path': remote_path,
                'size': file_size,
                'isdir': 0,
                'uploadid': upload_id,
                'block_list': json.dumps(block_list)
            }
            
            create_response = requests.post(create_url, params=create_params)
            create_result = create_response.json()
            
            if 'path' in create_result:
                logger.info(f"大文件上传成功: {remote_path}")
                # 删除断点续传信息
                self._delete_resume_info(local_path, remote_path)
                return True
            else:
                logger.error(f"合并分片失败: {create_result}")
                return False
                
        except Exception as e:
            logger.error(f"大文件上传失败: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str, **kwargs) -> bool:
        if not self.is_connected():
            logger.error("百度网盘未连接")
            return False
        
        params = {
            'method': 'download',
            'path': remote_path
        }
        
        result = self._api_request('/multimedia', params=params)
        
        if not result or 'link' not in result:
            logger.error("获取下载链接失败")
            return False
        
        try:
            download_url = result['link']
            response = requests.get(download_url, stream=True)
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"下载成功: {remote_path} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False
    
    def create_directory(self, path: str, **kwargs) -> bool:
        remote_path = kwargs.get('remote_path', path)
        params = {
            'method': 'create',
            'path': remote_path
        }
        
        result = self._api_request('/file', method="POST", params=params)
        
        if result and 'path' in result:
            logger.info(f"创建目录成功: {remote_path}")
            return True
        return False
    
    def delete(self, paths: List[str], **kwargs) -> bool:
        remote_paths = kwargs.get('remote_paths', paths)
        filelist = json.dumps(remote_paths)
        
        params = {
            'method': 'filemanager',
            'opera': 'delete',
            'filelist': filelist
        }
        
        result = self._api_request('/file', method="POST", params=params)
        
        if result:
            logger.info(f"删除成功: {remote_paths}")
            return True
        return False
    
    def get_user_info(self) -> Optional[Dict]:
        result = self._api_request('/nas', params={'method': 'uinfo'})
        
        if result:
            return {
                'username': result.get('username', ''),
                'vip_type': result.get('vip_type', 0),
                'total_size': result.get('total_size', 0),
                'used_size': result.get('used_size', 0)
            }
        return None


baidu_pan_service = BaiduPanService()