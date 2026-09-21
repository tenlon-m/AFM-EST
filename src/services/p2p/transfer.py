from typing import Dict, Optional, List
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

from .transfer_task import TransferTask, TransferStatus
from core.logger import logger as _logger


class TransferWorker(QThread):
    progress_updated = Signal(str, int)
    transfer_completed = Signal(str)
    transfer_failed = Signal(str, str)
    
    def __init__(self, task: TransferTask, parent=None):
        super().__init__(parent)
        
        self._task = task
        self._logger = _logger
        self._is_cancelled = False
        self._status_mutex = QMutex()
    
    def run(self) -> None:
        try:
            source_path = Path(self._task.source_path)
            target_path = Path(self._task.target_path)
            
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            self._task.start()
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            chunk_size = 8192
            transferred = 0
            
            with open(source_path, 'rb') as source_file:
                with open(target_path, 'wb') as target_file:
                    while not self._is_cancelled:
                        with QMutexLocker(self._status_mutex):
                            is_paused = self._task.status == TransferStatus.PAUSED
                        while is_paused:
                            self.msleep(100)
                            with QMutexLocker(self._status_mutex):
                                is_paused = self._task.status == TransferStatus.PAUSED
                        
                        chunk = source_file.read(chunk_size)
                        if not chunk:
                            break
                        
                        target_file.write(chunk)
                        transferred += len(chunk)
                        
                        self._task.update_progress(transferred)
                        self.progress_updated.emit(self._task.transfer_id, transferred)
            
            if self._is_cancelled:
                self._task.cancel()
            else:
                self._task.complete()
                self.transfer_completed.emit(self._task.transfer_id)
        
        except Exception as e:
            self._task.fail(str(e))
            self.transfer_failed.emit(self._task.transfer_id, str(e))
            self._logger.error(f"Transfer failed: {e}")
    
    def cancel(self) -> None:
        self._is_cancelled = True
    
    def get_task(self) -> TransferTask:
        return self._task


class FileTransfer(QObject):
    transfer_started = Signal(dict)
    transfer_progress = Signal(str, int, int)
    transfer_completed = Signal(dict)
    transfer_failed = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._logger = _logger
        self._tasks: Dict[str, TransferTask] = {}
        self._workers: Dict[str, TransferWorker] = {}
        self._mutex = QMutex()
    
    def send_file(self, source_path: str, target_path: str, transfer_id: Optional[str] = None) -> str:
        task = TransferTask.create(source_path, target_path, transfer_id)
        
        with QMutexLocker(self._mutex):
            self._tasks[task.transfer_id] = task
        
        worker = TransferWorker(task, self)
        worker.progress_updated.connect(self._on_progress_updated)
        worker.transfer_completed.connect(self._on_transfer_completed)
        worker.transfer_failed.connect(self._on_transfer_failed)
        
        with QMutexLocker(self._mutex):
            self._workers[task.transfer_id] = worker
        
        worker.start()
        self.transfer_started.emit(task.to_dict())
        self._logger.info(f"Transfer started: {source_path} -> {target_path}")
        
        return task.transfer_id
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        with QMutexLocker(self._mutex):
            worker = self._workers.get(transfer_id)
            if worker:
                worker.cancel()
                return True
        return False
    
    def pause_transfer(self, transfer_id: str) -> bool:
        with QMutexLocker(self._mutex):
            task = self._tasks.get(transfer_id)
            if task and task.status == TransferStatus.IN_PROGRESS:
                task.pause()
                return True
        return False
    
    def resume_transfer(self, transfer_id: str) -> bool:
        with QMutexLocker(self._mutex):
            task = self._tasks.get(transfer_id)
            if task and task.status == TransferStatus.PAUSED:
                task.resume()
                return True
        return False
    
    def _on_progress_updated(self, transfer_id: str, transferred: int) -> None:
        with QMutexLocker(self._mutex):
            task = self._tasks.get(transfer_id)
            if task:
                self.transfer_progress.emit(transfer_id, transferred, task.total_size)
    
    def _on_transfer_completed(self, transfer_id: str) -> None:
        with QMutexLocker(self._mutex):
            task = self._tasks.get(transfer_id)
            worker = self._workers.pop(transfer_id, None)
            
            if worker:
                worker.deleteLater()
        
        if task:
            self.transfer_completed.emit(task.to_dict())
            self._logger.info(f"Transfer completed: {task.source_path}")
    
    def _on_transfer_failed(self, transfer_id: str, error: str) -> None:
        with QMutexLocker(self._mutex):
            worker = self._workers.pop(transfer_id, None)
            
            if worker:
                worker.deleteLater()
        
        self.transfer_failed.emit(transfer_id, error)
        self._logger.error(f"Transfer failed: {transfer_id} - {error}")
    
    def get_task(self, transfer_id: str) -> Optional[TransferTask]:
        with QMutexLocker(self._mutex):
            return self._tasks.get(transfer_id)
    
    def get_active_tasks(self) -> List[TransferTask]:
        with QMutexLocker(self._mutex):
            return [
                task for task in self._tasks.values()
                if task.is_active
            ]
    
    def get_all_tasks(self) -> List[TransferTask]:
        with QMutexLocker(self._mutex):
            return list(self._tasks.values())
    
    def cancel_all(self) -> None:
        with QMutexLocker(self._mutex):
            for transfer_id, worker in self._workers.items():
                worker.cancel()
            workers_to_wait = list(self._workers.items())
            self._workers.clear()
            cancelled_ids = list(self._tasks.keys())
        
        for transfer_id, worker in workers_to_wait:
            worker.wait(3000)
            worker.deleteLater()
        
        with QMutexLocker(self._mutex):
            for transfer_id in cancelled_ids:
                task = self._tasks.pop(transfer_id, None)
                if task:
                    task.cancel()