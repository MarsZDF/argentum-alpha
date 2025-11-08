"""
Request deduplication.
"""
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import threading

@dataclass
class DuplicateDetectionResult:
    is_duplicate: bool
    original_request_id: Optional[str] = None
    similarity_score: float = 0.0
    cached_response: Optional[Any] = None

class RequestDeduplicator:
    def __init__(self, enable_semantic_matching: bool = True, similarity_threshold: float = 0.85, ttl_seconds: int = 3600):
        self.enable_semantic_matching = enable_semantic_matching
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}
        self._request_map: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    def check_duplicate(self, request_id: str, prompt: str) -> DuplicateDetectionResult:
        fingerprint = self._fingerprint(prompt)
        with self._lock:
            if fingerprint in self._cache:
                response, timestamp = self._cache[fingerprint]
                if (datetime.utcnow() - timestamp).total_seconds() < self.ttl_seconds:
                    self._request_map[request_id] = fingerprint
                    return DuplicateDetectionResult(True, self._find_original_request(fingerprint), 1.0, response)
                else:
                    del self._cache[fingerprint]
        return DuplicateDetectionResult(False)
    
    def cache_response(self, request_id: str, prompt: str, response: Any):
        fingerprint = self._fingerprint(prompt)
        with self._lock:
            self._cache[fingerprint] = (response, datetime.utcnow())
            self._request_map[request_id] = fingerprint
    
    def _fingerprint(self, prompt: str) -> str:
        normalized = " ".join(prompt.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _find_original_request(self, fingerprint: str) -> Optional[str]:
        for req_id, fp in self._request_map.items():
            if fp == fingerprint:
                return req_id
        return None
