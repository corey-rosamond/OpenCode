"""Web response caching."""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from .types import FetchOptions, FetchResponse

logger = logging.getLogger(__name__)


class WebCache:
    """Cache for web responses.

    Thread-safe: uses RLock for all cache operations.
    """

    def __init__(
        self,
        max_size: int = 100 * 1024 * 1024,
        ttl: int = 900,
        cache_dir: Path | None = None,
    ):
        """Initialize cache.

        Args:
            max_size: Maximum cache size in bytes
            ttl: Time-to-live in seconds
            cache_dir: Directory for cache files (memory if None)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache_dir = cache_dir
        # key -> (timestamp, size, data)
        self._memory_cache: dict[str, tuple[float, int, dict[str, Any]]] = {}
        self._current_size = 0
        self._lock = threading.RLock()

        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_key(
        self,
        url: str,
        options: FetchOptions | None = None,  # noqa: ARG002
    ) -> str:
        """Generate cache key for URL.

        The cache key is based on the URL only. User-agent and other options
        are NOT included because:
        1. Most websites return the same content regardless of user-agent
        2. Including user-agent would fragment the cache unnecessarily
        3. The same URL should return cached content even if options change

        Args:
            url: URL to cache
            options: Fetch options (not used in key generation)

        Returns:
            Cache key string (32-char hex digest)
        """
        # Only URL affects cache key
        return hashlib.sha256(url.encode()).hexdigest()[:32]

    def get(self, key: str) -> FetchResponse | None:
        """Get cached response.

        Thread-safe: uses lock.

        Args:
            key: Cache key

        Returns:
            Cached response or None
        """
        with self._lock:
            # Check memory cache
            if key in self._memory_cache:
                timestamp, size, data = self._memory_cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.debug(f"Cache hit (memory): {key}")
                    response = self._deserialize_response(data)
                    response.from_cache = True
                    return response
                else:
                    # Expired - update size tracking
                    self._current_size -= size
                    del self._memory_cache[key]

        # Check file cache (outside lock for I/O)
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                stat = cache_file.stat()
                if time.time() - stat.st_mtime < self.ttl:
                    logger.debug(f"Cache hit (file): {key}")
                    data = json.loads(cache_file.read_text())
                    response = self._deserialize_response(data)
                    response.from_cache = True
                    return response
                else:
                    # Expired
                    cache_file.unlink()

        return None

    def set(self, key: str, response: FetchResponse) -> None:
        """Cache a response.

        Thread-safe: uses lock.

        Args:
            key: Cache key
            response: Response to cache
        """
        data = self._serialize_response(response)

        # Estimate size (do serialization outside lock)
        serialized = json.dumps(data)
        size = len(serialized)

        with self._lock:
            # Remove old entry if exists (update size tracking)
            if key in self._memory_cache:
                _, old_size, _ = self._memory_cache[key]
                self._current_size -= old_size
                del self._memory_cache[key]

            # Check if we need to evict
            while self._current_size + size > self.max_size:
                if not self._evict_oldest():
                    break

            # Store in memory with size tracking
            self._memory_cache[key] = (time.time(), size, data)
            self._current_size += size

        # Store to file (outside lock for I/O)
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(serialized)

        logger.debug(f"Cached: {key}")

    def delete(self, key: str) -> bool:
        """Delete cached entry.

        Thread-safe: uses lock.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        deleted = False

        with self._lock:
            if key in self._memory_cache:
                _, size, _ = self._memory_cache[key]
                self._current_size -= size
                del self._memory_cache[key]
                deleted = True

        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
                deleted = True

        return deleted

    def clear(self) -> int:
        """Clear all cache entries.

        Thread-safe: uses lock.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._memory_cache)
            self._memory_cache.clear()
            self._current_size = 0

        if self.cache_dir:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()
                count += 1

        logger.info(f"Cleared {count} cache entries")
        return count

    def _evict_oldest(self) -> bool:
        """Evict oldest cache entry.

        Note: Caller must hold lock.
        """
        if not self._memory_cache:
            return False

        # Find oldest
        oldest_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k][0],
        )

        _, size, _ = self._memory_cache[oldest_key]
        self._current_size -= size
        del self._memory_cache[oldest_key]
        return True

    def _serialize_response(self, response: FetchResponse) -> dict[str, Any]:
        """Serialize response for caching.

        Note: Uses surrogateescape for binary content to preserve original bytes
        in a recoverable form. This avoids silent corruption from 'replace'.
        """
        content = response.content
        if isinstance(content, bytes):
            # Use surrogateescape to preserve non-UTF-8 bytes in a recoverable form
            # This is better than 'replace' which silently corrupts data
            content = content.decode("utf-8", errors="surrogateescape")

        return {
            "url": response.url,
            "final_url": response.final_url,
            "status_code": response.status_code,
            "content_type": response.content_type,
            "content": content,
            "headers": response.headers,
            "encoding": response.encoding,
            "fetch_time": response.fetch_time,
        }

    def _deserialize_response(self, data: dict[str, Any]) -> FetchResponse:
        """Deserialize cached response."""
        return FetchResponse(
            url=data["url"],
            final_url=data["final_url"],
            status_code=data["status_code"],
            content_type=data["content_type"],
            content=data["content"],
            headers=data["headers"],
            encoding=data["encoding"],
            fetch_time=data["fetch_time"],
            from_cache=True,
        )

    @property
    def size(self) -> int:
        """Get current cache size in bytes."""
        with self._lock:
            return self._current_size

    @property
    def count(self) -> int:
        """Get number of cached entries."""
        with self._lock:
            return len(self._memory_cache)
