"""API caching and rate limiting utilities."""
import time
import json
from pathlib import Path
from typing import Optional, Callable, Any


class APICache:
    """Simple file-based cache for API responses with TTL."""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / ".cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_file(self, key: str) -> Path:
        """Get path to cache file for given key."""
        # Simple sanitization of key for filename
        safe_key = key.replace('/', '_').replace(':', '_')
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, ttl_seconds: int, fetch_func: Callable[[], Any]) -> Any:
        """
        Get cached data or fetch fresh data if cache is stale.

        Args:
            key: Unique cache key
            ttl_seconds: Time-to-live in seconds
            fetch_func: Function to call to fetch fresh data

        Returns:
            Cached or fresh data
        """
        cache_file = self.get_cache_file(key)

        # Check if cache exists and is valid
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)

                # Check if cache is still valid
                if time.time() - cached['timestamp'] < ttl_seconds:
                    return cached['data']
            except (json.JSONDecodeError, KeyError):
                # Invalid cache file, will re-fetch
                pass

        # Cache miss or stale, fetch fresh data
        fresh_data = fetch_func()

        # Store in cache
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'data': fresh_data
            }, f)

        return fresh_data

    def clear(self, key: Optional[str] = None):
        """Clear cache for specific key or all cache."""
        if key:
            cache_file = self.get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
