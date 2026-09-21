from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path


class TransferStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransferTask:
    transfer_id: str
    source_path: str
    target_path: str
    total_size: int
    transferred_size: int = 0
    status: TransferStatus = TransferStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _paused_duration: float = field(default=0.0, init=False, repr=False)
    _last_pause_time: Optional[datetime] = field(default=None, init=False, repr=False)
    
    @property
    def progress_percentage(self) -> float:
        if self.total_size == 0:
            return 0.0
        return (self.transferred_size / self.total_size) * 100
    
    @property
    def is_completed(self) -> bool:
        return self.status == TransferStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        return self.status == TransferStatus.FAILED
    
    @property
    def is_active(self) -> bool:
        return self.status in (TransferStatus.PENDING, TransferStatus.IN_PROGRESS, TransferStatus.PAUSED)
    
    def start(self) -> None:
        self.status = TransferStatus.IN_PROGRESS
        self.start_time = datetime.now()
    
    def pause(self) -> None:
        if self.status == TransferStatus.IN_PROGRESS:
            self.status = TransferStatus.PAUSED
            self._last_pause_time = datetime.now()
    
    def resume(self) -> None:
        if self.status == TransferStatus.PAUSED:
            self.status = TransferStatus.IN_PROGRESS
            if self._last_pause_time:
                self._paused_duration += (datetime.now() - self._last_pause_time).total_seconds()
                self._last_pause_time = None
    
    def complete(self) -> None:
        self.status = TransferStatus.COMPLETED
        self.transferred_size = self.total_size
        self.end_time = datetime.now()
    
    def fail(self, error_message: str) -> None:
        self.status = TransferStatus.FAILED
        self.error_message = error_message
        self.end_time = datetime.now()
    
    def cancel(self) -> None:
        self.status = TransferStatus.CANCELLED
        self.end_time = datetime.now()
    
    def update_progress(self, transferred: int) -> None:
        self.transferred_size = min(transferred, self.total_size)
    
    def get_speed(self) -> Optional[float]:
        if self.start_time is None or self.transferred_size == 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        effective_elapsed = elapsed - self._paused_duration
        if self._last_pause_time and self.status == TransferStatus.PAUSED:
            effective_elapsed -= (datetime.now() - self._last_pause_time).total_seconds()
        
        if effective_elapsed <= 0:
            return None
        
        return self.transferred_size / effective_elapsed
    
    def get_remaining_time(self) -> Optional[float]:
        speed = self.get_speed()
        if speed is None or speed == 0:
            return None
        
        remaining_size = self.total_size - self.transferred_size
        return remaining_size / speed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'transfer_id': self.transfer_id,
            'source_path': self.source_path,
            'target_path': self.target_path,
            'total_size': self.total_size,
            'transferred_size': self.transferred_size,
            'status': self.status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransferTask':
        start_time = None
        if data.get('start_time'):
            try:
                start_time = datetime.fromisoformat(data['start_time'])
            except ValueError:
                pass
        
        end_time = None
        if data.get('end_time'):
            try:
                end_time = datetime.fromisoformat(data['end_time'])
            except ValueError:
                pass
        
        return cls(
            transfer_id=data['transfer_id'],
            source_path=data['source_path'],
            target_path=data['target_path'],
            total_size=data['total_size'],
            transferred_size=data.get('transferred_size', 0),
            status=TransferStatus(data.get('status', 'pending')),
            start_time=start_time,
            end_time=end_time,
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {}),
        )
    
    @classmethod
    def create(cls, source_path: str, target_path: str, transfer_id: Optional[str] = None) -> 'TransferTask':
        import uuid
        
        source = Path(source_path)
        total_size = source.stat().st_size if source.exists() else 0
        
        return cls(
            transfer_id=transfer_id or str(uuid.uuid4()),
            source_path=source_path,
            target_path=target_path,
            total_size=total_size,
        )