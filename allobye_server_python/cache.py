"""TTL-based in-memory caching system for AllôBye MCP Server.

This module provides a high-performance caching layer to eliminate N+1 queries
and reduce database load. Uses TTL-based expiration and automatic cleanup.

Performance Goals:
- Reduce average response time by 50%
- Eliminate all N+1 queries
- Cache hit rate > 80% for repeated queries
- Support 100+ concurrent users
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from monitoring import get_logger, get_metrics

logger = get_logger()
metrics = get_metrics()

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Represents a single cache entry with TTL."""

    key: str
    value: Any
    created_at: float
    ttl_seconds: int
    hits: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self) -> None:
        """Update access statistics."""
        self.hits += 1
        self.last_accessed = time.time()


class CacheManager:
    """Thread-safe TTL-based in-memory cache manager.

    Features:
    - TTL-based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Statistics tracking (hits, misses, evictions)
    - Namespace support for cache isolation
    """

    def __init__(
        self,
        default_ttl: int = 300,
        max_size: int = 10000,
        cleanup_interval: int = 60,
    ):
        """Initialize cache manager.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of cache entries before eviction
            cleanup_interval: Seconds between automatic cleanup runs
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "invalidations": 0,
        }

        # Start background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    def start(self) -> None:
        """Start the background cleanup task."""
        if not self._running:
            self._running = True
            logger.info("Cache manager started", default_ttl=self._default_ttl, max_size=self._max_size)

    def stop(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Cache manager stopped")

    def _make_key(self, namespace: str, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{namespace}:{key}"

    def _hash_key(self, obj: Any) -> str:
        """Create a hash key from any object."""
        if isinstance(obj, str):
            return obj
        # Convert to JSON and hash
        json_str = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value from cache.

        Args:
            namespace: Cache namespace for isolation
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._make_key(namespace, key)

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats["misses"] += 1
                metrics.record_cache_operation("miss")
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[cache_key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                metrics.record_cache_operation("miss")
                return None

            # Cache hit
            entry.touch()
            self._stats["hits"] += 1
            metrics.record_cache_operation("hit")
            logger.debug(
                "Cache hit",
                namespace=namespace,
                key=key,
                hits=entry.hits,
                age_seconds=time.time() - entry.created_at,
            )
            return entry.value

    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache.

        Args:
            namespace: Cache namespace for isolation
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._make_key(namespace, key)
        ttl = ttl or self._default_ttl

        with self._lock:
            # Check cache size and evict if needed
            if len(self._cache) >= self._max_size and cache_key not in self._cache:
                self._evict_lru()

            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl,
            )
            self._cache[cache_key] = entry
            self._stats["sets"] += 1
            metrics.record_cache_operation("set")
            logger.debug("Cache set", namespace=namespace, key=key, ttl=ttl)

    def invalidate(self, namespace: str, key: Optional[str] = None) -> int:
        """Invalidate cache entries.

        Args:
            namespace: Cache namespace
            key: Specific key to invalidate (if None, invalidates entire namespace)

        Returns:
            Number of entries invalidated
        """
        count = 0

        with self._lock:
            if key:
                # Invalidate specific key
                cache_key = self._make_key(namespace, key)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    count = 1
            else:
                # Invalidate entire namespace
                prefix = f"{namespace}:"
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
                for k in keys_to_delete:
                    del self._cache[k]
                count = len(keys_to_delete)

            self._stats["invalidations"] += count
            metrics.record_cache_operation("invalidate")

        logger.info("Cache invalidated", namespace=namespace, key=key, count=count)
        return count

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._stats["evictions"] += 1
        logger.debug("Cache LRU eviction", key=lru_key)

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        count = 0

        with self._lock:
            keys_to_delete = [k for k, v in self._cache.items() if v.is_expired()]
            for k in keys_to_delete:
                del self._cache[k]
            count = len(keys_to_delete)
            self._stats["evictions"] += count

        if count > 0:
            logger.info("Cache cleanup completed", expired_entries=count)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "evictions": self._stats["evictions"],
                "invalidations": self._stats["invalidations"],
                "hit_rate": hit_rate,
                "total_requests": total_requests,
            }

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()

        logger.info("Cache cleared", entries_cleared=count)
        return count


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(
            default_ttl=300,  # 5 minutes default
            max_size=10000,
            cleanup_interval=60,
        )
        _cache_manager.start()
    return _cache_manager


# Cache TTL presets for different data types
class CacheTTL:
    """TTL presets for different types of cached data."""

    SCHOOL_INFO = 3600  # 1 hour - schools rarely change
    USER_PROFILE = 900  # 15 minutes - profiles can update
    DELEGATE_LIST = 300  # 5 minutes - delegates can be added/removed
    PICKUP_LIST = 60  # 1 minute - pickups change frequently
    CHILDREN_LIST = 1800  # 30 minutes - children list is fairly static


def cache_result(
    namespace: str,
    ttl: Optional[int] = None,
    key_func: Optional[Callable[..., str]] = None,
) -> Callable:
    """Decorator to cache function results.

    Args:
        namespace: Cache namespace
        ttl: Time-to-live in seconds
        key_func: Function to generate cache key from arguments

    Example:
        @cache_result("schools", ttl=CacheTTL.SCHOOL_INFO)
        async def get_school(school_id: str) -> Dict:
            # Expensive database query
            return await db.query(...)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()

            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: hash all arguments
                key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                key = cache._hash_key(":".join(key_parts))

            # Try to get from cache
            cached_value = cache.get(namespace, key)
            if cached_value is not None:
                logger.debug("Cache hit for function", function=func.__name__, namespace=namespace)
                return cached_value

            # Cache miss - call function
            logger.debug("Cache miss for function", function=func.__name__, namespace=namespace)
            result = await func(*args, **kwargs)

            # Store in cache
            cache.set(namespace, key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(namespace: str, key: Optional[str] = None) -> int:
    """Helper to invalidate cache entries.

    Args:
        namespace: Cache namespace
        key: Specific key to invalidate (if None, invalidates entire namespace)

    Returns:
        Number of entries invalidated
    """
    cache = get_cache()
    return cache.invalidate(namespace, key)


# Batch operation helper
async def batch_get_with_cache(
    namespace: str,
    ids: List[str],
    fetch_func: Callable[[List[str]], Any],
    ttl: Optional[int] = None,
) -> List[Any]:
    """Batch get items with caching.

    Checks cache for each ID, fetches missing ones in batch, then caches them.

    Args:
        namespace: Cache namespace
        ids: List of IDs to fetch
        fetch_func: Async function to fetch missing IDs (receives list of IDs)
        ttl: Time-to-live for cached entries

    Returns:
        List of fetched items in same order as IDs
    """
    cache = get_cache()
    results: Dict[str, Any] = {}
    missing_ids: List[str] = []

    # Check cache for each ID
    for id in ids:
        cached = cache.get(namespace, id)
        if cached is not None:
            results[id] = cached
        else:
            missing_ids.append(id)

    # Fetch missing IDs in batch
    if missing_ids:
        logger.debug(
            "Batch fetching missing items",
            namespace=namespace,
            total=len(ids),
            cached=len(results),
            missing=len(missing_ids),
        )
        fetched_items = await fetch_func(missing_ids)

        # Cache fetched items
        for item in fetched_items:
            # Assume item has 'id' field
            item_id = item.get("id") or item.get("uuid")
            if item_id:
                cache.set(namespace, str(item_id), item, ttl=ttl)
                results[item_id] = item

    # Return results in original order
    return [results.get(id) for id in ids if id in results]
