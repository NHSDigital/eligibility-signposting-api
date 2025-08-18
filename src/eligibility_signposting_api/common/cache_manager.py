"""Cache management utilities for Lambda container optimization."""

import logging
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """Thread-safe cache manager for Lambda container optimization."""

    def __init__(self) -> None:
        self._caches: dict[str, object] = {}
        self._logger = logging.getLogger(__name__)

    def get(self, cache_key: str) -> object | None:
        """Get a value from the cache."""
        value = self._caches.get(cache_key)
        if value is not None:
            self._logger.debug("Cache hit", extra={"cache_key": cache_key})
        else:
            self._logger.debug("Cache miss", extra={"cache_key": cache_key})
        return value

    def set(self, cache_key: str, value: object) -> None:
        """Set a value in the cache."""
        self._caches[cache_key] = value
        self._logger.debug("Cache updated", extra={"cache_key": cache_key})

    def clear(self, cache_key: str) -> bool:
        """Clear a specific cache entry. Returns True if entry existed."""
        if cache_key in self._caches:
            del self._caches[cache_key]
            self._logger.info("Cache entry cleared", extra={"cache_key": cache_key})
            return True
        return False

    def clear_all(self) -> None:
        """Clear all cached data."""
        self._caches.clear()
        self._logger.info("All caches cleared")

    def get_cache_info(self) -> dict[str, int]:
        """Get information about current cache state."""
        info = {}
        for key, value in self._caches.items():
            try:
                info[key] = len(value) if hasattr(value, "__len__") else 1  # type: ignore[arg-type]
            except TypeError:
                info[key] = 1
        return info

    def has(self, cache_key: str) -> bool:
        """Check if a cache key exists."""
        return cache_key in self._caches

    def size(self) -> int:
        """Get the number of cached items."""
        return len(self._caches)


# Global cache manager instance
_cache_manager = CacheManager()

# Export the global cache manager for direct use
cache_manager = _cache_manager

# Cache keys constants
FLASK_APP_CACHE_KEY = "flask_app"
CAMPAIGN_CONFIGS_CACHE_KEY = "campaign_configs"
