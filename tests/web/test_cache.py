"""Tests for web cache."""

import tempfile
import time
from pathlib import Path

import pytest

from code_forge.web.cache import WebCache
from code_forge.web.types import FetchOptions, FetchResponse


def make_response(
    url: str = "https://example.com",
    content: str = "test content",
    from_cache: bool = False,
) -> FetchResponse:
    """Create a test response."""
    return FetchResponse(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        content=content,
        headers={},
        encoding="utf-8",
        fetch_time=0.1,
        from_cache=from_cache,
    )


class TestWebCache:
    """Tests for WebCache."""

    def test_initialization(self) -> None:
        """Test cache initialization."""
        cache = WebCache()
        assert cache.max_size == 100 * 1024 * 1024
        assert cache.ttl == 900
        assert cache.size == 0
        assert cache.count == 0

    def test_initialization_custom(self) -> None:
        """Test cache with custom values."""
        cache = WebCache(max_size=1024, ttl=60)
        assert cache.max_size == 1024
        assert cache.ttl == 60

    def test_initialization_with_dir(self) -> None:
        """Test cache with directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = WebCache(cache_dir=cache_dir)
            assert cache_dir.exists()

    def test_generate_key(self) -> None:
        """Test cache key generation."""
        cache = WebCache()
        key1 = cache.generate_key("https://example.com")
        key2 = cache.generate_key("https://example.com")
        key3 = cache.generate_key("https://other.com")

        assert key1 == key2  # Same URL = same key
        assert key1 != key3  # Different URL = different key
        assert len(key1) == 32  # SHA256 truncated to 32 chars

    def test_generate_key_ignores_options(self) -> None:
        """Test that options don't affect cache key."""
        cache = WebCache()
        opts1 = FetchOptions(user_agent="Agent1")
        opts2 = FetchOptions(user_agent="Agent2")

        key1 = cache.generate_key("https://example.com", opts1)
        key2 = cache.generate_key("https://example.com", opts2)

        assert key1 == key2

    def test_set_and_get(self) -> None:
        """Test storing and retrieving from cache."""
        cache = WebCache()
        response = make_response()

        cache.set("key1", response)
        cached = cache.get("key1")

        assert isinstance(cached, FetchResponse)
        assert cached.url == response.url
        assert cached.content == response.content
        assert cached.from_cache is True

    def test_get_miss(self) -> None:
        """Test cache miss returns None."""
        cache = WebCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self) -> None:
        """Test that entries expire after TTL."""
        cache = WebCache(ttl=1)  # 1 second TTL
        response = make_response()

        cache.set("key1", response)
        assert cache.get("key1") is not None

        time.sleep(1.1)  # Wait for expiration
        assert cache.get("key1") is None

    def test_delete(self) -> None:
        """Test deleting cache entry."""
        cache = WebCache()
        response = make_response()

        cache.set("key1", response)
        assert cache.get("key1") is not None

        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self) -> None:
        """Test deleting nonexistent entry."""
        cache = WebCache()
        result = cache.delete("nonexistent")
        assert result is False

    def test_clear(self) -> None:
        """Test clearing all entries."""
        cache = WebCache()

        cache.set("key1", make_response("https://a.com"))
        cache.set("key2", make_response("https://b.com"))
        cache.set("key3", make_response("https://c.com"))

        count = cache.clear()
        assert count == 3
        assert cache.count == 0
        assert cache.size == 0

    def test_size_tracking(self) -> None:
        """Test that size is tracked correctly."""
        cache = WebCache()
        assert cache.size == 0

        cache.set("key1", make_response(content="x" * 100))
        size_after_one = cache.size
        assert size_after_one > 0

        cache.set("key2", make_response(content="x" * 100))
        assert cache.size > size_after_one

    def test_count_tracking(self) -> None:
        """Test that count is tracked correctly."""
        cache = WebCache()
        assert cache.count == 0

        cache.set("key1", make_response())
        assert cache.count == 1

        cache.set("key2", make_response())
        assert cache.count == 2

        cache.delete("key1")
        assert cache.count == 1

    def test_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        cache = WebCache(max_size=500)  # Small cache

        # Add entries until eviction happens
        for i in range(20):
            cache.set(f"key{i}", make_response(content=f"content{i}" * 10))

        # Cache should have evicted old entries
        assert cache.size <= 500

    def test_update_existing_key(self) -> None:
        """Test updating existing cache entry."""
        cache = WebCache()

        cache.set("key1", make_response(content="original"))
        cache.set("key1", make_response(content="updated"))

        cached = cache.get("key1")
        assert isinstance(cached, FetchResponse)
        assert cached.content == "updated"
        assert cache.count == 1

    def test_file_cache(self) -> None:
        """Test file-based caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = WebCache(cache_dir=cache_dir)

            response = make_response()
            cache.set("key1", response)

            # Check file was created
            cache_file = cache_dir / "key1.json"
            assert cache_file.exists()

            # Delete from memory, should still get from file
            cache._memory_cache.clear()
            cache._current_size = 0

            cached = cache.get("key1")
            assert isinstance(cached, FetchResponse)
            assert cached.content == response.content

    def test_file_cache_clear(self) -> None:
        """Test clearing file cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = WebCache(cache_dir=cache_dir)

            cache.set("key1", make_response())
            cache.set("key2", make_response())

            count = cache.clear()
            assert count >= 2
            assert not list(cache_dir.glob("*.json"))

    def test_file_cache_delete(self) -> None:
        """Test deleting from file cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = WebCache(cache_dir=cache_dir)

            cache.set("key1", make_response())
            cache_file = cache_dir / "key1.json"
            assert cache_file.exists()

            cache.delete("key1")
            assert not cache_file.exists()

    def test_file_cache_expiration(self) -> None:
        """Test file cache respects TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = WebCache(cache_dir=cache_dir, ttl=1)

            cache.set("key1", make_response())

            # Clear memory to force file read
            cache._memory_cache.clear()
            cache._current_size = 0

            time.sleep(1.1)
            assert cache.get("key1") is None

    def test_binary_content(self) -> None:
        """Test caching binary content."""
        cache = WebCache()
        response = FetchResponse(
            url="https://example.com/image.png",
            final_url="https://example.com/image.png",
            status_code=200,
            content_type="image/png",
            content=b"\x89PNG\r\n",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )

        cache.set("key1", response)
        cached = cache.get("key1")

        assert isinstance(cached, FetchResponse)
        # Binary content is decoded when cached
        assert isinstance(cached.content, str)

    def test_thread_safety(self) -> None:
        """Test thread-safe operations."""
        import threading

        cache = WebCache()
        errors: list[Exception] = []

        def worker(prefix: str) -> None:
            try:
                for i in range(100):
                    cache.set(f"{prefix}_{i}", make_response())
                    cache.get(f"{prefix}_{i}")
                    if i % 10 == 0:
                        cache.delete(f"{prefix}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
