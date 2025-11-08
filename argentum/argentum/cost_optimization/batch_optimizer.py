"""
Request batching optimizer.
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

class BatchStrategy(Enum):
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"

@dataclass
class BatchRequest:
    request_id: str
    prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Batch:
    batch_id: str
    requests: List[BatchRequest]
    created_at: datetime
    max_size: int
    timeout_seconds: int

class BatchOptimizer:
    def __init__(self, max_batch_size: int = 10, timeout_seconds: int = 5,
                 strategy: BatchStrategy = BatchStrategy.HYBRID,
                 on_batch_ready: Optional[Callable] = None):
        self.max_batch_size = max_batch_size
        self.timeout_seconds = timeout_seconds
        self.strategy = strategy
        self.on_batch_ready = on_batch_ready
        self._pending_requests: List[BatchRequest] = []
        self._lock = threading.Lock()
        self._batch_counter = 0
        self._last_batch_time = datetime.utcnow()
    
    def add_request(self, request_id: str, prompt: str, metadata: Optional[Dict] = None) -> Optional[Batch]:
        request = BatchRequest(request_id=request_id, prompt=prompt, metadata=metadata or {})
        with self._lock:
            self._pending_requests.append(request)
            return self._check_batch_ready()
    
    def get_batch(self, force: bool = False) -> Optional[Batch]:
        with self._lock:
            if force and self._pending_requests:
                return self._create_batch()
            return self._check_batch_ready()
    
    def _check_batch_ready(self) -> Optional[Batch]:
        if not self._pending_requests:
            return None
        if len(self._pending_requests) >= self.max_batch_size:
            batch = self._create_batch()
            if self.on_batch_ready:
                self.on_batch_ready(batch)
            return batch
        return None
    
    def _create_batch(self) -> Batch:
        self._batch_counter += 1
        batch_requests = self._pending_requests[:self.max_batch_size]
        self._pending_requests = self._pending_requests[self.max_batch_size:]
        batch = Batch(f"batch_{self._batch_counter}", batch_requests, datetime.utcnow(),
                     self.max_batch_size, self.timeout_seconds)
        self._last_batch_time = datetime.utcnow()
        return batch
