"""
Intelligent caching layer for AI agent responses.
"""
import hashlib
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import threading

class CacheHit:
    def __init__(self, key: str, value: Any, age_seconds: float):
        self.key = key
        self.value = value
        self.age_seconds = age_seconds

class CacheMiss:
    def __init__(self, key: str):
        self.key = key

@dataclass
class CacheConfig:
    ttl_seconds: int = 3600
    max_size: int = 1000
    enable_semantic_cache: bool = True
    semantic_threshold: float = 0.85

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    size: int = 0
    evictions: int = 0
    cost_saved: float = 0.0

class CacheLayer:
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
        self._stats = CacheStats()
    
    def get(self, key: str):
        cache_key = self._normalize_key(key)
        with self._lock:
            self._stats.total_requests += 1
            if cache_key in self._cache:
                value, expiration = self._cache[cache_key]
                if time.time() < expiration:
                    self._stats.hits += 1
                    self._update_hit_rate()
                    age = time.time() - (expiration - self.config.ttl_seconds)
                    return CacheHit(cache_key, value, age)
                else:
                    del self._cache[cache_key]
            self._stats.misses += 1
            self._update_hit_rate()
            return CacheMiss(cache_key)
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        cache_key = self._normalize_key(key)
        ttl = ttl_seconds or self.config.ttl_seconds
        expiration = time.time() + ttl
        with self._lock:
            if len(self._cache) >= self.config.max_size and cache_key not in self._cache:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                self._stats.evictions += 1
            self._cache[cache_key] = (value, expiration)
            self._stats.size = len(self._cache)
    
    def get_stats(self) -> CacheStats:
        with self._lock:
            self._stats.cost_saved = self._stats.hits * 0.01
            return CacheStats(hits=self._stats.hits, misses=self._stats.misses,
                            total_requests=self._stats.total_requests, hit_rate=self._stats.hit_rate,
                            size=self._stats.size, evictions=self._stats.evictions,
                            cost_saved=self._stats.cost_saved)
    
    def _normalize_key(self, key: str) -> str:
        return " ".join(key.strip().split())
    
    def _update_hit_rate(self):
        if self._stats.total_requests > 0:
            self._stats.hit_rate = self._stats.hits / self._stats.total_requests
        else:
            self._stats.hit_rate = 0.0
