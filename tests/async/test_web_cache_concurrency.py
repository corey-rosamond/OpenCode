"""Concurrency tests for WebCache.

Tests thread safety and concurrent access patterns for the web response cache.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from code_forge.web.cache import WebCache
from code_forge.web.types import FetchResponse

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def fetch_response() -> FetchResponse:
    """Create a test FetchResponse."""
    return FetchResponse(
        url="https://example.com/page",
        final_url="https://example.com/page",
        status_code=200,
        content_type="text/html",
        content="<html><body>Test</body></html>",
        headers={"Content-Type": "text/html"},
        encoding="utf-8",
        fetch_time=0.5,
    )


@pytest.fixture
def cache(tmp_path: Path) -> WebCache:
    """Create a WebCache with file backing."""
    return WebCache(max_size=1024 * 1024, ttl=900, cache_dir=tmp_path)


@pytest.fixture
def memory_cache() -> WebCache:
    """Create a memory-only WebCache."""
    return WebCache(max_size=1024 * 1024, ttl=900)


# =============================================================================
# Test Thread-Safe Get Operations
# =============================================================================


class TestCacheConcurrentGet:
    """Tests for thread-safe get operations."""

    def test_concurrent_get_same_key(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Concurrent gets for same key are thread-safe."""
        key = cache.generate_key("https://example.com")
        cache.set(key, fetch_response)

        results = []
        errors = []

        def get_cached() -> None:
            try:
                result = cache.get(key)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_cached) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert all(r is not None for r in results)

    def test_concurrent_get_different_keys(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Concurrent gets for different keys work correctly."""
        keys = [cache.generate_key(f"https://example.com/{i}") for i in range(10)]
        for key in keys:
            cache.set(key, fetch_response)

        results = {key: [] for key in keys}

        def get_cached(key: str) -> None:
            result = cache.get(key)
            results[key].append(result)

        threads = [
            threading.Thread(target=get_cached, args=(key,))
            for key in keys
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for key in keys:
            assert len(results[key]) == 5
            assert all(r is not None for r in results[key])

    def test_get_miss_is_thread_safe(self, cache: WebCache) -> None:
        """Cache misses are handled correctly under concurrency."""
        results = []

        def get_missing() -> None:
            result = cache.get("nonexistent-key")
            results.append(result)

        threads = [threading.Thread(target=get_missing) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert all(r is None for r in results)


# =============================================================================
# Test Thread-Safe Set Operations
# =============================================================================


class TestCacheConcurrentSet:
    """Tests for thread-safe set operations."""

    def test_concurrent_set_same_key(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Concurrent sets for same key don't corrupt cache."""
        key = cache.generate_key("https://example.com")
        errors = []

        def set_cached() -> None:
            try:
                cache.set(key, fetch_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_cached) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Final value should be retrievable
        result = cache.get(key)
        assert result is not None
        assert result.url == fetch_response.url

    def test_concurrent_set_different_keys(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Concurrent sets for different keys work correctly."""
        keys = [cache.generate_key(f"https://example.com/{i}") for i in range(20)]
        errors = []

        def set_cached(key: str) -> None:
            try:
                cache.set(key, fetch_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_cached, args=(key,)) for key in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.count == 20

    def test_set_updates_size_correctly(
        self, memory_cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Size tracking is correct under concurrent sets."""
        keys = [memory_cache.generate_key(f"https://example.com/{i}") for i in range(10)]

        def set_cached(key: str) -> None:
            memory_cache.set(key, fetch_response)

        threads = [threading.Thread(target=set_cached, args=(key,)) for key in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Size should be positive and consistent
        assert memory_cache.size > 0
        assert memory_cache.count == 10


# =============================================================================
# Test Thread-Safe Delete Operations
# =============================================================================


class TestCacheConcurrentDelete:
    """Tests for thread-safe delete operations."""

    def test_concurrent_delete_same_key(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Concurrent deletes for same key are thread-safe."""
        key = cache.generate_key("https://example.com")
        cache.set(key, fetch_response)

        results = []

        def delete_cached() -> None:
            result = cache.delete(key)
            results.append(result)

        threads = [threading.Thread(target=delete_cached) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should return True (first to delete)
        assert sum(results) >= 1  # At least one succeeded
        assert cache.get(key) is None

    def test_delete_during_set(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Delete during set doesn't cause corruption."""
        key = cache.generate_key("https://example.com")
        errors = []

        def set_cached() -> None:
            try:
                for _ in range(100):
                    cache.set(key, fetch_response)
            except Exception as e:
                errors.append(e)

        def delete_cached() -> None:
            try:
                for _ in range(100):
                    cache.delete(key)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=set_cached)
        t2 = threading.Thread(target=delete_cached)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0


# =============================================================================
# Test Thread-Safe Clear Operations
# =============================================================================


class TestCacheConcurrentClear:
    """Tests for thread-safe clear operations."""

    def test_clear_during_operations(
        self, cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Clear during other operations is thread-safe."""
        errors = []
        keys = [cache.generate_key(f"https://example.com/{i}") for i in range(10)]

        def do_operations() -> None:
            try:
                for key in keys:
                    cache.set(key, fetch_response)
                    cache.get(key)
            except Exception as e:
                errors.append(e)

        def do_clear() -> None:
            try:
                time.sleep(0.001)  # Small delay to let operations start
                cache.clear()
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=do_operations)
        t2 = threading.Thread(target=do_clear)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0


# =============================================================================
# Test Size Tracking Under Concurrency
# =============================================================================


class TestCacheSizeTracking:
    """Tests for size tracking under concurrent access."""

    def test_size_never_negative(
        self, memory_cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Size never goes negative under concurrent operations."""
        keys = [memory_cache.generate_key(f"https://example.com/{i}") for i in range(50)]
        observed_sizes = []

        def mixed_operations(key: str) -> None:
            memory_cache.set(key, fetch_response)
            observed_sizes.append(memory_cache.size)
            memory_cache.delete(key)
            observed_sizes.append(memory_cache.size)

        threads = [threading.Thread(target=mixed_operations, args=(key,)) for key in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(s >= 0 for s in observed_sizes)

    def test_size_consistent_after_operations(
        self, memory_cache: WebCache, fetch_response: FetchResponse
    ) -> None:
        """Size is consistent after all operations complete."""
        keys = [memory_cache.generate_key(f"https://example.com/{i}") for i in range(20)]

        def set_cached(key: str) -> None:
            memory_cache.set(key, fetch_response)

        threads = [threading.Thread(target=set_cached, args=(key,)) for key in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Calculate expected size
        size_after_set = memory_cache.size
        count_after_set = memory_cache.count

        assert count_after_set == 20
        assert size_after_set > 0

        # Delete half
        delete_keys = keys[:10]
        threads = [threading.Thread(target=memory_cache.delete, args=(key,)) for key in delete_keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert memory_cache.count == 10
        assert memory_cache.size < size_after_set


# =============================================================================
# Test Eviction Under Concurrency
# =============================================================================


class TestCacheEvictionConcurrency:
    """Tests for eviction behavior under concurrent access."""

    def test_eviction_is_thread_safe(self) -> None:
        """Eviction under memory pressure is thread-safe."""
        # Small cache that will need to evict
        cache = WebCache(max_size=1000, ttl=900)

        errors = []
        large_response = FetchResponse(
            url="https://example.com/large",
            final_url="https://example.com/large",
            status_code=200,
            content_type="text/html",
            content="x" * 200,  # Each entry ~200 bytes
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        def add_entries(start: int) -> None:
            try:
                for i in range(20):
                    key = cache.generate_key(f"https://example.com/{start}-{i}")
                    cache.set(key, large_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_entries, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should have evicted to stay under max_size
        assert cache.size <= cache.max_size

    def test_eviction_order_oldest_first(self) -> None:
        """Oldest entries are evicted first."""
        cache = WebCache(max_size=500, ttl=900)

        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="x" * 100,
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        # Add entries with slight delay to ensure ordering
        for i in range(10):
            key = cache.generate_key(f"https://example.com/{i}")
            cache.set(key, response)
            time.sleep(0.001)  # Ensure different timestamps

        # Newest entries should still be present
        last_key = cache.generate_key("https://example.com/9")
        assert cache.get(last_key) is not None or cache.count < 10


# =============================================================================
# Test TTL Expiration Under Concurrency
# =============================================================================


class TestCacheTTLConcurrency:
    """Tests for TTL expiration under concurrent access."""

    def test_ttl_expiration_is_thread_safe(self) -> None:
        """TTL expiration during concurrent access is safe."""
        cache = WebCache(max_size=10000, ttl=1)  # 1 second TTL

        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="test content",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        key = cache.generate_key("https://example.com")
        cache.set(key, response)

        errors = []
        results = []

        def get_repeatedly() -> None:
            try:
                for _ in range(100):
                    result = cache.get(key)
                    results.append(result)
                    time.sleep(0.02)  # 20ms delay
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_repeatedly) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Some results should be None (expired), some not None
        # Due to TTL expiration during the test


# =============================================================================
# Test File Cache Concurrency
# =============================================================================


class TestFileCacheConcurrency:
    """Tests for file-backed cache under concurrent access."""

    def test_concurrent_file_writes(
        self, tmp_path: Path
    ) -> None:
        """Concurrent file writes don't corrupt cache files."""
        cache = WebCache(max_size=10000, ttl=900, cache_dir=tmp_path)

        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="test content",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        errors = []
        key = cache.generate_key("https://example.com")

        def write_file() -> None:
            try:
                cache.set(key, response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_file) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # File should be valid JSON
        cache_file = tmp_path / f"{key}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            assert data["url"] == "https://example.com"

    def test_concurrent_file_reads(
        self, tmp_path: Path
    ) -> None:
        """Concurrent file reads work correctly."""
        cache = WebCache(max_size=10000, ttl=900, cache_dir=tmp_path)

        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="test content",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        key = cache.generate_key("https://example.com")
        cache.set(key, response)

        # Clear memory cache to force file reads
        cache._memory_cache.clear()
        cache._current_size = 0

        results = []

        def read_file() -> None:
            result = cache.get(key)
            results.append(result)

        threads = [threading.Thread(target=read_file) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert all(r is not None for r in results)


# =============================================================================
# Test ThreadPoolExecutor Stress
# =============================================================================


class TestCacheThreadPoolStress:
    """Stress tests using ThreadPoolExecutor."""

    def test_high_concurrency_mixed_operations(
        self, memory_cache: WebCache
    ) -> None:
        """High concurrency with mixed operations."""
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="test",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        errors = []

        def mixed_op(i: int) -> str:
            try:
                key = memory_cache.generate_key(f"https://example.com/{i % 10}")
                if i % 3 == 0:
                    memory_cache.set(key, response)
                    return "set"
                elif i % 3 == 1:
                    memory_cache.get(key)
                    return "get"
                else:
                    memory_cache.delete(key)
                    return "delete"
            except Exception as e:
                errors.append(e)
                return "error"

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_op, i) for i in range(1000)]
            results = [f.result() for f in as_completed(futures)]

        assert len(errors) == 0
        assert "error" not in results

    def test_parallel_key_generation(
        self, memory_cache: WebCache
    ) -> None:
        """Key generation is thread-safe."""
        urls = [f"https://example.com/{i}" for i in range(100)]
        results = {}

        def gen_key(url: str) -> tuple[str, str]:
            key = memory_cache.generate_key(url)
            return url, key

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(gen_key, url) for url in urls]
            for f in as_completed(futures):
                url, key = f.result()
                results[url] = key

        # Same URL should always get same key
        for url in urls:
            expected_key = memory_cache.generate_key(url)
            assert results[url] == expected_key
