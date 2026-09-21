from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class P2PConnectionState:
    device_id: str
    socket_address: Optional[str] = None
    is_connected: bool = False
    connection_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    heartbeat_timeout: int = 30
    retry_count: int = 0
    max_retries: int = 5
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.connection_time is None and self.is_connected:
            self.connection_time = datetime.now()
        if self.last_heartbeat is None and self.is_connected:
            self.last_heartbeat = datetime.now()
    
    def update_heartbeat(self) -> None:
        self.last_heartbeat = datetime.now()
    
    def is_heartbeat_timeout(self) -> bool:
        if not self.is_connected:
            return False
        if self.last_heartbeat is None:
            return True
        
        elapsed = datetime.now() - self.last_heartbeat
        return elapsed.total_seconds() > self.heartbeat_timeout
    
    def should_retry(self) -> bool:
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        self.retry_count += 1
    
    def reset_retry(self) -> None:
        self.retry_count = 0
    
    def mark_connected(self, socket_address: str) -> None:
        self.is_connected = True
        self.socket_address = socket_address
        self.connection_time = datetime.now()
        self.last_heartbeat = datetime.now()
        self.retry_count = 0
    
    def mark_disconnected(self) -> None:
        self.is_connected = False
        self.socket_address = None
        self.retry_count = 0
    
    def get_connection_duration(self) -> Optional[timedelta]:
        if self.connection_time is None:
            return None
        return datetime.now() - self.connection_time
    
    def to_dict(self) -> Dict:
        return {
            'device_id': self.device_id,
            'socket_address': self.socket_address,
            'is_connected': self.is_connected,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'heartbeat_timeout': self.heartbeat_timeout,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'P2PConnectionState':
        connection_time = None
        if data.get('connection_time'):
            try:
                connection_time = datetime.fromisoformat(data['connection_time'])
            except ValueError:
                pass
        
        last_heartbeat = None
        if data.get('last_heartbeat'):
            try:
                last_heartbeat = datetime.fromisoformat(data['last_heartbeat'])
            except ValueError:
                pass
        
        return cls(
            device_id=data['device_id'],
            socket_address=data.get('socket_address'),
            is_connected=data.get('is_connected', False),
            connection_time=connection_time,
            last_heartbeat=last_heartbeat,
            heartbeat_timeout=data.get('heartbeat_timeout', 30),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 5),
            metadata=data.get('metadata', {}),
        )