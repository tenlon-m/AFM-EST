#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2P服务单元测试
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.p2p.p2p_service import P2PService
from services.p2p.p2p_device import P2PDevice


class TestP2PService(unittest.TestCase):
    """P2P服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(self.test_file, 'w') as f:
            f.write('Hello, P2P!')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.temp_dir)
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_p2p_init(self, mock_transfer, mock_connection, mock_discovery):
        """测试P2P服务初始化"""
        p2p = P2PService()
        
        self.assertFalse(p2p.enabled)
        mock_discovery.assert_called_once()
        mock_connection.assert_called_once()
        mock_transfer.assert_called_once()
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_discover_devices(self, mock_transfer, mock_connection, mock_discovery):
        """测试设备发现"""
        mock_discovery_instance = Mock()
        mock_discovery.return_value = mock_discovery_instance
        mock_discovery_instance.get_devices.return_value = []
        
        p2p = P2PService()
        devices = p2p.discover_devices()
        
        self.assertEqual(devices, [])
        mock_discovery_instance.start_discovery.assert_called_once()
        mock_discovery_instance.get_devices.assert_called_once()
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_stop_discovery(self, mock_transfer, mock_connection, mock_discovery):
        """测试停止设备发现"""
        mock_discovery_instance = Mock()
        mock_discovery.return_value = mock_discovery_instance
        
        p2p = P2PService()
        p2p.stop_discovery()
        
        mock_discovery_instance.stop_discovery.assert_called_once()
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_connect_device(self, mock_transfer, mock_connection, mock_discovery):
        """测试连接设备"""
        mock_connection_instance = Mock()
        mock_connection.return_value = mock_connection_instance
        
        p2p = P2PService()
        device = P2PDevice('test_device', 'Test Device', '192.168.1.100', 50001)
        
        p2p.connect(device)
        
        mock_connection_instance.connect_to_device.assert_called_with(device)
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_disconnect_device(self, mock_transfer, mock_connection, mock_discovery):
        """测试断开设备连接"""
        mock_connection_instance = Mock()
        mock_connection.return_value = mock_connection_instance
        
        p2p = P2PService()
        p2p.disconnect('test_device')
        
        mock_connection_instance.disconnect.assert_called_with('test_device')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_send_file(self, mock_transfer, mock_connection, mock_discovery):
        """测试发送文件"""
        mock_transfer_instance = Mock()
        mock_transfer_instance.send_file.return_value = 'transfer_001'
        mock_transfer.return_value = mock_transfer_instance
        
        p2p = P2PService()
        transfer_id = p2p.send_file(self.test_file, '/remote/test.txt')
        
        self.assertEqual(transfer_id, 'transfer_001')
        mock_transfer_instance.send_file.assert_called_with(self.test_file, '/remote/test.txt', None)
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_send_file_with_id(self, mock_transfer, mock_connection, mock_discovery):
        """测试使用指定ID发送文件"""
        mock_transfer_instance = Mock()
        mock_transfer_instance.send_file.return_value = 'custom_id'
        mock_transfer.return_value = mock_transfer_instance
        
        p2p = P2PService()
        transfer_id = p2p.send_file(self.test_file, '/remote/test.txt', transfer_id='custom_id')
        
        self.assertEqual(transfer_id, 'custom_id')
        mock_transfer_instance.send_file.assert_called_with(self.test_file, '/remote/test.txt', 'custom_id')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_cancel_transfer(self, mock_transfer, mock_connection, mock_discovery):
        """测试取消传输"""
        mock_transfer_instance = Mock()
        mock_transfer_instance.cancel_transfer.return_value = True
        mock_transfer.return_value = mock_transfer_instance
        
        p2p = P2PService()
        result = p2p.cancel_transfer('transfer_001')
        
        self.assertTrue(result)
        mock_transfer_instance.cancel_transfer.assert_called_with('transfer_001')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_pause_transfer(self, mock_transfer, mock_connection, mock_discovery):
        """测试暂停传输"""
        mock_transfer_instance = Mock()
        mock_transfer_instance.pause_transfer.return_value = True
        mock_transfer.return_value = mock_transfer_instance
        
        p2p = P2PService()
        result = p2p.pause_transfer('transfer_001')
        
        self.assertTrue(result)
        mock_transfer_instance.pause_transfer.assert_called_with('transfer_001')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_resume_transfer(self, mock_transfer, mock_connection, mock_discovery):
        """测试恢复传输"""
        mock_transfer_instance = Mock()
        mock_transfer_instance.resume_transfer.return_value = True
        mock_transfer.return_value = mock_transfer_instance
        
        p2p = P2PService()
        result = p2p.resume_transfer('transfer_001')
        
        self.assertTrue(result)
        mock_transfer_instance.resume_transfer.assert_called_with('transfer_001')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_get_devices(self, mock_transfer, mock_connection, mock_discovery):
        """测试获取设备列表"""
        mock_discovery_instance = Mock()
        mock_discovery_instance.get_devices.return_value = []
        mock_discovery.return_value = mock_discovery_instance
        
        p2p = P2PService()
        devices = p2p.get_devices()
        
        self.assertEqual(devices, [])
        mock_discovery_instance.get_devices.assert_called_once()
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_get_device(self, mock_transfer, mock_connection, mock_discovery):
        """测试获取单个设备"""
        mock_discovery_instance = Mock()
        mock_device = P2PDevice('test_device', 'Test Device', '192.168.1.100', 50001)
        mock_discovery_instance.get_device.return_value = mock_device
        mock_discovery.return_value = mock_discovery_instance
        
        p2p = P2PService()
        device = p2p.get_device('test_device')
        
        self.assertEqual(device.device_id, 'test_device')
        mock_discovery_instance.get_device.assert_called_with('test_device')
    
    @patch('services.p2p.p2p_service.DeviceDiscovery')
    @patch('services.p2p.p2p_service.ConnectionManager')
    @patch('services.p2p.p2p_service.FileTransfer')
    def test_get_nonexistent_device(self, mock_transfer, mock_connection, mock_discovery):
        """测试获取不存在的设备"""
        mock_discovery_instance = Mock()
        mock_discovery_instance.get_device.return_value = None
        mock_discovery.return_value = mock_discovery_instance
        
        p2p = P2PService()
        device = p2p.get_device('nonexistent')
        
        self.assertIsNone(device)


class TestP2PDevice(unittest.TestCase):
    """P2P设备测试"""
    
    def test_device_init(self):
        """测试设备初始化"""
        device = P2PDevice('test_device', 'Test Device', '192.168.1.100', 50001)
        
        self.assertEqual(device.device_id, 'test_device')
        self.assertEqual(device.ip_address, '192.168.1.100')
        self.assertEqual(device.hostname, 'Test Device')
    
    def test_device_repr(self):
        """测试设备字符串表示"""
        device = P2PDevice('test_device', 'Test Device', '192.168.1.100', 50001)
        
        repr_str = repr(device)
        self.assertIn('test_device', repr_str)
        self.assertIn('192.168.1.100', repr_str)


if __name__ == '__main__':
    unittest.main()
