from typing import Dict, Optional
from datetime import datetime
import threading

from PySide6.QtCore import QObject, Signal, QTimer, QByteArray
from PySide6.QtNetwork import QTcpSocket, QHostAddress

from .p2p_device import P2PDevice
from .connection_state import P2PConnectionState
from core.logger import logger as _logger


class ConnectionManager(QObject):
    connection_established = Signal(str)
    connection_lost = Signal(str)
    connection_error = Signal(str, str)
    heartbeat_timeout = Signal(str)
    data_received = Signal(str, bytes)
    
    DEFAULT_PORT = 50001
    HEARTBEAT_INTERVAL = 10
    
    def __init__(self, port: int = DEFAULT_PORT, parent=None):
        super().__init__(parent)
        
        self._port = port
        self._logger = _logger
        self._connections: Dict[str, P2PConnectionState] = {}
        self._sockets: Dict[str, QTcpSocket] = {}
        self._lock = threading.Lock()
        
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._send_heartbeats)
        
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_connections)
    
    def _start_timers_if_needed(self):
        if not self._heartbeat_timer.isActive():
            self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL * 1000)
        if not self._check_timer.isActive():
            self._check_timer.start(5000)
    
    def connect_to_device(self, device: P2PDevice) -> None:
        device_id = device.device_id
        
        with self._lock:
            already_connected = device_id in self._connections and self._connections[device_id].is_connected
        
        if already_connected:
            self.connection_established.emit(device_id)
            return
        
        socket = QTcpSocket(self)
        socket.connectToHost(QHostAddress(device.ip_address), device.port)
        
        connection_state = P2PConnectionState(device_id=device_id)
        with self._lock:
            self._connections[device_id] = connection_state
            self._sockets[device_id] = socket
        
        socket.connected.connect(lambda did=device_id: self._on_connected(did))
        socket.disconnected.connect(lambda did=device_id: self._on_disconnected(did))
        socket.errorOccurred.connect(lambda error, did=device_id: self._on_error(did, error))
        socket.readyRead.connect(lambda did=device_id: self._on_data_ready(did))
        
        self._logger.info(f"Connecting to device: {device.hostname} ({device.get_address()})")
    
    def disconnect(self, device_id: str) -> None:
        with self._lock:
            if device_id not in self._sockets:
                return
            
            socket = self._sockets.pop(device_id, None)
            self._connections.pop(device_id, None)
        
        if socket:
            socket.disconnectFromHost()
            socket.deleteLater()
        
        self._logger.info(f"Disconnected from device: {device_id}")
    
    def _on_connected(self, device_id: str) -> None:
        with self._lock:
            if device_id not in self._connections:
                return
            
            socket = self._sockets.get(device_id)
            if socket:
                address = f"{socket.peerAddress().toString()}:{socket.peerPort()}"
                self._connections[device_id].mark_connected(address)
        
        self._start_timers_if_needed()
        self.connection_established.emit(device_id)
        self._logger.info(f"Connection established: {device_id}")
    
    def _on_disconnected(self, device_id: str) -> None:
        with self._lock:
            if device_id in self._connections:
                self._connections[device_id].mark_disconnected()
        
        self.connection_lost.emit(device_id)
        self._logger.info(f"Connection lost: {device_id}")
    
    def _on_error(self, device_id: str, error) -> None:
        with self._lock:
            socket = self._sockets.get(device_id)
            error_string = socket.errorString() if socket else str(error)
            
            if device_id in self._connections:
                self._connections[device_id].mark_disconnected()
        
        self.connection_error.emit(device_id, error_string)
        self._logger.error(f"Connection error for {device_id}: {error_string}")
    
    def _on_data_ready(self, device_id: str) -> None:
        with self._lock:
            socket = self._sockets.get(device_id)
        
        if not socket:
            return
        
        data = None
        try:
            data = socket.readAll().data()
        except Exception as e:
            _logger.debug(f"读取socket数据失败: {device_id} - {e}")
            return
        
        if data:
            with self._lock:
                if device_id in self._connections:
                    self._connections[device_id].update_heartbeat()
            self.data_received.emit(device_id, data)
    
    def _send_heartbeats(self) -> None:
        import json
        
        with self._lock:
            socket_items = list(self._sockets.items())
        
        for device_id, socket in socket_items:
            if socket and socket.state() == QTcpSocket.ConnectedState:
                try:
                    heartbeat = {
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat(),
                    }
                    data = json.dumps(heartbeat).encode('utf-8')
                    socket.write(data)
                    socket.flush()
                except Exception as e:
                    self._logger.error(f"Failed to send heartbeat to {device_id}: {e}")
    
    def _check_connections(self) -> None:
        with self._lock:
            timeout_devices = []
            for device_id, state in self._connections.items():
                if state.is_connected and state.is_heartbeat_timeout():
                    timeout_devices.append(device_id)
        
        for device_id in timeout_devices:
            self.heartbeat_timeout.emit(device_id)
            self._logger.warning(f"Heartbeat timeout for {device_id}")
    
    def is_connected(self, device_id: str) -> bool:
        with self._lock:
            state = self._connections.get(device_id)
            return state.is_connected if state else False
    
    def get_connection_state(self, device_id: str) -> Optional[P2PConnectionState]:
        with self._lock:
            return self._connections.get(device_id)
    
    def get_connected_devices(self) -> list:
        with self._lock:
            return [
                device_id for device_id, state in self._connections.items()
                if state.is_connected
            ]
    
    def disconnect_all(self) -> None:
        with self._lock:
            device_ids = list(self._sockets.keys())
        
        for device_id in device_ids:
            self.disconnect(device_id)
    
    def stop_timers(self) -> None:
        self._heartbeat_timer.stop()
        self._check_timer.stop()
