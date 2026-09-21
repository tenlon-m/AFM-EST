from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .discovery import DeviceDiscovery
from .connection import ConnectionManager
from .transfer import FileTransfer
from .p2p_device import P2PDevice
from .transfer_task import TransferTask
from core.logger import logger as _logger


class P2PService(QObject):
    device_found = Signal(dict)
    device_lost = Signal(str)
    connection_established = Signal(str)
    connection_lost = Signal(str)
    connection_error = Signal(str, str)
    heartbeat_timeout = Signal(str)
    transfer_progress = Signal(str, int, int)
    transfer_completed = Signal(dict)
    transfer_failed = Signal(str, str)
    discovery_completed = Signal(list)
    
    def __init__(self, discovery_port: int = 50000, connection_port: int = 50001, parent=None):
        super().__init__(parent)
        
        self._logger = _logger
        self.enabled = False  # P2P服务启用状态
        
        self._discovery = DeviceDiscovery(discovery_port, self)
        self._connection = ConnectionManager(connection_port, self)
        self._transfer = FileTransfer(self)
        self._transfer_request_callback = None
        
        self._connect_signals()
    
    def _connect_signals(self) -> None:
        self._discovery.device_found.connect(self.device_found)
        self._discovery.device_lost.connect(self.device_lost)
        
        self._connection.connection_established.connect(self.connection_established)
        self._connection.connection_lost.connect(self.connection_lost)
        self._connection.connection_error.connect(self.connection_error)
        self._connection.heartbeat_timeout.connect(self.heartbeat_timeout)
        self._connection.data_received.connect(self._on_data_received)
        
        self._transfer.transfer_progress.connect(self.transfer_progress)
        self._transfer.transfer_completed.connect(self.transfer_completed)
        self._transfer.transfer_failed.connect(self.transfer_failed)
    
    def _on_data_received(self, device_id: str, data: bytes) -> None:
        import json
        try:
            message = json.loads(data.decode('utf-8'))
            msg_type = message.get('type', '')
            if msg_type == 'transfer_request' and hasattr(self, '_transfer_request_callback') and self._transfer_request_callback:
                self._transfer_request_callback(
                    task_id=message.get('task_id', ''),
                    filename=message.get('filename', ''),
                    filesize=message.get('filesize', 0),
                    hostname=message.get('hostname', ''),
                    ip=message.get('ip', ''),
                    address=message.get('address', ''),
                )
        except Exception as e:
            self._logger.debug(f"Failed to parse data from {device_id}: {e}")
    
    def discover_devices(self, async_mode: bool = False) -> Optional[List[P2PDevice]]:
        self._discovery.start_discovery()
        
        if async_mode:
            from PySide6.QtCore import QTimer
            
            def on_discovery_timeout():
                devices = self._discovery.get_devices()
                device_dicts = [d.to_dict() for d in devices]
                self.discovery_completed.emit(device_dicts)
            
            QTimer.singleShot(2000, on_discovery_timeout)
            return None
        else:
            import time
            time.sleep(2)
            return self._discovery.get_devices()
    
    def stop_discovery(self) -> None:
        self._discovery.stop_discovery()
    
    def connect(self, device: P2PDevice) -> None:
        self._connection.connect_to_device(device)
    
    def disconnect(self, device_id: str) -> None:
        self._connection.disconnect(device_id)
    
    def send_file(self, source_path: str, target_path: str, transfer_id: Optional[str] = None) -> str:
        return self._transfer.send_file(source_path, target_path, transfer_id)
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        return self._transfer.cancel_transfer(transfer_id)
    
    def pause_transfer(self, transfer_id: str) -> bool:
        return self._transfer.pause_transfer(transfer_id)
    
    def resume_transfer(self, transfer_id: str) -> bool:
        return self._transfer.resume_transfer(transfer_id)
    
    def get_devices(self) -> List[P2PDevice]:
        return self._discovery.get_devices()
    
    def get_device(self, device_id: str) -> Optional[P2PDevice]:
        return self._discovery.get_device(device_id)
    
    def is_connected(self, device_id: str) -> bool:
        return self._connection.is_connected(device_id)
    
    def shutdown(self) -> None:
        self._transfer.cancel_all()
        self._connection.disconnect_all()
        self._connection.stop_timers()
        self.stop_discovery()
        self.enabled = False
        self._logger.info("P2P service shutdown")
    
    def get_connected_devices(self) -> list:
        return self._connection.get_connected_devices()
    
    def get_active_transfers(self) -> List[TransferTask]:
        return self._transfer.get_active_tasks()
    
    def get_transfer(self, transfer_id: str) -> Optional[TransferTask]:
        return self._transfer.get_task(transfer_id)
    
    def set_transfer_request_callback(self, callback) -> None:
        self._transfer_request_callback = callback