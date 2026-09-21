#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP服务单元测试
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.ftp_service import FTPConnection


class TestFTPConnection(unittest.TestCase):
    """FTP连接测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(self.test_file, 'w') as f:
            f.write('Hello, FTP!')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.temp_dir)
    
    @patch('ftplib.FTP')
    def test_ftp_connect(self, mock_ftp):
        """测试FTP连接"""
        mock_conn = Mock()
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        result = ftp.connect()
        
        self.assertTrue(result)
        self.assertTrue(ftp.connected)
        mock_conn.connect.assert_called_with('localhost', 21)
        mock_conn.login.assert_called_with('user', 'pass')
    
    @patch('ftplib.FTP')
    def test_ftp_disconnect(self, mock_ftp):
        """测试FTP断开连接"""
        mock_conn = Mock()
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        ftp.disconnect()
        
        self.assertFalse(ftp.connected)
        mock_conn.quit.assert_called_once()
    
    @patch('ftplib.FTP')
    def test_ftp_get_current_path(self, mock_ftp):
        """测试获取当前路径"""
        mock_conn = Mock()
        mock_conn.pwd.return_value = '/home/user'
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        path = ftp.get_current_path()
        
        self.assertEqual(path, '/home/user')
        mock_conn.pwd.assert_called_once()
    
    @patch('ftplib.FTP')
    def test_ftp_change_dir(self, mock_ftp):
        """测试切换目录"""
        mock_conn = Mock()
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        result = ftp.change_dir('/home/user')
        
        self.assertTrue(result)
        self.assertEqual(ftp.current_path, '/home/user')
        mock_conn.cwd.assert_called_with('/home/user')
    
    @patch('ftplib.FTP')
    def test_ftp_change_dir_failure(self, mock_ftp):
        """测试切换目录失败"""
        mock_conn = Mock()
        mock_conn.cwd.side_effect = Exception('Directory not found')
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        result = ftp.change_dir('/nonexistent')
        
        self.assertFalse(result)
    
    @patch('ftplib.FTP')
    def test_ftp_list_files(self, mock_ftp):
        """测试列出文件"""
        mock_conn = Mock()
        mock_conn.pwd.return_value = '/'
        
        def retrlines_side_effect(cmd, callback):
            callback('type=file;size=123;modify=20240101120000; test.txt')
            callback('type=directory;modify=20240101120000; docs')
        
        mock_conn.retrlines.side_effect = retrlines_side_effect
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        files = ftp.list_files()
        
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]['name'], 'test.txt')
        self.assertEqual(files[0]['type'], 'file')
        self.assertEqual(files[0]['size'], 123)
        self.assertEqual(files[1]['name'], 'docs')
        self.assertEqual(files[1]['type'], 'directory')
    
    @patch('ftplib.FTP')
    def test_ftp_download_file(self, mock_ftp):
        """测试下载文件"""
        mock_conn = Mock()
        mock_conn.size.return_value = 12
        
        def retrbinary_callback(cmd, callback):
            callback(b'Hello, FTP!')
        
        mock_conn.retrbinary.side_effect = retrbinary_callback
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        local_path = os.path.join(self.temp_dir, 'downloaded.txt')
        result = ftp.download_file('/remote/test.txt', local_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'Hello, FTP!')
    
    @patch('ftplib.FTP')
    def test_ftp_upload_file(self, mock_ftp):
        """测试上传文件"""
        mock_conn = Mock()
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        result = ftp.upload_file(self.test_file, '/remote/test.txt')
        
        self.assertTrue(result)
        mock_conn.storbinary.assert_called_once()
    
    @patch('ftplib.FTP')
    def test_ftp_upload_nonexistent_file(self, mock_ftp):
        """测试上传不存在的文件"""
        mock_conn = Mock()
        mock_ftp.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        ftp.connect()
        result = ftp.upload_file('/nonexistent/file.txt', '/remote/test.txt')
        
        self.assertFalse(result)
    
    @patch('ftplib.FTP')
    def test_ftp_not_connected(self, mock_ftp):
        """测试未连接状态下的操作"""
        ftp = FTPConnection('localhost', 21, 'user', 'pass')
        
        result = ftp.list_files()
        self.assertEqual(result, [])
        
        result = ftp.download_file('/remote/test.txt', '/local/test.txt')
        self.assertFalse(result)
        
        result = ftp.upload_file('/local/test.txt', '/remote/test.txt')
        self.assertFalse(result)
        
        result = ftp.change_dir('/home')
        self.assertFalse(result)
    
    @patch('ftplib.FTP_TLS')
    def test_ftps_connect(self, mock_ftps):
        """测试FTPS连接"""
        mock_conn = Mock()
        mock_ftps.return_value = mock_conn
        
        ftp = FTPConnection('localhost', 990, 'user', 'pass', protocol='ftps')
        result = ftp.connect()
        
        self.assertTrue(result)
        self.assertTrue(ftp.connected)
        mock_conn.connect.assert_called_with('localhost', 990)
        mock_conn.login.assert_called_with('user', 'pass')
    
    def test_invalid_protocol(self):
        """测试无效协议类型"""
        ftp = FTPConnection('localhost', 21, 'user', 'pass', protocol='invalid')
        result = ftp.connect()
        
        self.assertFalse(result)
        self.assertFalse(ftp.connected)


if __name__ == '__main__':
    unittest.main()
