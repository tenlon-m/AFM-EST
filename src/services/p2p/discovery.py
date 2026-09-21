from typing import List, Dict, Optional
from datetime import datetime, timedelta
import threading

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QUdpSocket, QHostAddress

from .p2p_device import P2PDevice, DeviceStatus
from core.logger import logger as _logger


class DeviceDiscovery(QObject):
    device_found = Signal(dict)
    device_lost = Signal(str)
    discovery_started = Signal()
    discovery_stopped = Signal()
    
    DEFAULT_BROADCAST_PORT = 50000
    DEFAULT_DISCOVERY_INTERVAL = 10
    DEVICE_TIMEOUT = 30
    
    def __init__(self, port: int = DEFAULT_BROADCAST_PORT, parent=None):
        super().__init__(parent)
        
        self._port = port
        self._logger = _logger
        self._devices: Dict[str, P2PDevice] = {}
        self._lock = threading.Lock()
        self._is_discovering = False
        
        self._udp_socket = QUdpSocket(self)
        self._udp_socket.readyRead.connect(self._on_datagram_received)
        
        self._discovery_timer = QTimer(self)
        self._discovery_timer.timeout.connect(self._send_broadcast)
        
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_devices)
    
    def start_discovery(self) -> None:
        if self._is_discovering:
            return
        
        self._is_discovering = True
        self._udp_socket.bind(QHostAddress.Any, self._port)
        self._cleanup_timer.start(5000)
        self._discovery_timer.start(self.DEFAULT_DISCOVERY_INTERVAL * 1000)
        self._send_broadcast()
        self.discovery_started.emit()
        self._logger.info("Device discovery started")
    
    def stop_discovery(self) -> None:
        if not self._is_discovering:
            return
        
        self._is_discovering = False
        self._discovery_timer.stop()
        self._cleanup_timer.stop()
        try:
            self._udp_socket.close()
        except Exception as e:
            self._logger.debug(f"操作失败: {e}")
        self.discovery_stopped.emit()
        self._logger.info("Device discovery stopped")
    
    def _send_broadcast(self) -> None:
        import socket
        import json
        
        local_ip = self._get_local_ip()
        
        message = {
            'type': 'discovery',
            'device_id': self._get_device_id(),
            'hostname': socket.gethostname(),
            'ip_address': local_ip,
            'port': self._port,
            'timestamp': datetime.now().isoformat(),
        }
        
        data = json.dumps(message).encode('utf-8')
        
        self._udp_socket.writeDatagram(
            data,
            QHostAddress.Broadcast,
            self._port
        )
    
    def _on_datagram_received(self) -> None:
        import json
        
        while self._udp_socket.hasPendingDatagrams():
            datagram = self._udp_socket.receiveDatagram()
            data = datagram.data().data().decode('utf-8')
            
            try:
                message = json.loads(data)
                
                if message.get('type') == 'discovery':
                    self._handle_discovery_message(message)
            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self._logger.error(f"Error handling datagram: {e}")
    
    def _handle_discovery_message(self, message: Dict) -> None:
        device_id = message.get('device_id')
        
        if device_id == self._get_device_id():
            return
        
        device = P2PDevice(
            device_id=device_id,
            hostname=message.get('hostname', 'Unknown'),
            ip_address=message.get('ip_address', '0.0.0.0'),
            port=message.get('port', self.DEFAULT_BROADCAST_PORT),
            status=DeviceStatus.ONLINE,
            last_seen=datetime.now(),
        )
        
        should_emit = False
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].update_last_seen()
            else:
                self._devices[device_id] = device
                should_emit = True
        
        if should_emit:
            self.device_found.emit(device.to_dict())
            self._logger.info(f"Device found: {device.hostname} ({device.get_address()})")
    
    def _cleanup_devices(self) -> None:
        now = datetime.now()
        timeout = timedelta(seconds=self.DEVICE_TIMEOUT)
        
        devices_to_remove = []
        
        with self._lock:
            for device_id, device in self._devices.items():
                if device.last_seen and (now - device.last_seen) > timeout:
                    devices_to_remove.append(device_id)
            
            removed_devices = []
            for device_id in devices_to_remove:
                device = self._devices.pop(device_id)
                removed_devices.append(device)
        
        for device in removed_devices:
            self.device_lost.emit(device.device_id)
            self._logger.info(f"Device lost: {device.hostname}")
    
    def _get_device_id(self) -> str:
        import socket
        import uuid
        
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 48, 8)][::-1])
        return f"{hostname}-{mac}"
    
    def _get_local_ip(self) -> str:
        import socket
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return ip
        except Exception as e:
            self._logger.debug(f"操作失败: {e}")
            return "0.0.0.0"
        finally:
            if s:
                s.close()
    
    def get_devices(self) -> List[P2PDevice]:
        with self._lock:
            return list(self._devices.values())
    
    def get_device(self, device_id: str) -> Optional[P2PDevice]:
        with self._lock:
            return self._devices.get(device_id)
    
    def get_device_count(self) -> int:
        with self._lock:
            return len(self._devices)
    
    def is_discovering(self) -> bool:
        return self._is_discovering