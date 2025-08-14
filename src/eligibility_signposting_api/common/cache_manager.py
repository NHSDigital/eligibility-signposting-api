"""Cache management utilities for Lambda container optimization."""

import logging
from typing import TypeVar

logger = logging.getLogger(__name__)

# Global cache storage
_caches: dict[str, object] = {}

T = TypeVar("T")


def get_cache(cache_key: str) -> object | None:
    """Get a value from the global cache."""
    return _caches.get(cache_key)


def set_cache(cache_key: str, value: object) -> None:
    """Set a value in the global cache."""
    _caches[cache_key] = value
    logger.debug("Cache updated", extra={"cache_key": cache_key})


def clear_cache(cache_key: str) -> None:
    """Clear a specific cache entry."""
    if cache_key in _caches:
        del _caches[cache_key]
        logger.info("Cache entry cleared", extra={"cache_key": cache_key})


def clear_all_caches() -> None:
    """Clear all cached data."""
    _caches.clear()
    logger.info("All caches cleared")


def get_cache_info() -> dict[str, int]:
    """Get information about current cache state."""
    info = {}
    for key, value in _caches.items():
        try:
            info[key] = len(value) if hasattr(value, "__len__") else 1  # type: ignore[arg-type]
        except TypeError:
            info[key] = 1
    return info


# Cache keys constants
FLASK_APP_CACHE_KEY = "flask_app"
CAMPAIGN_CONFIGS_CACHE_KEY = "campaign_configs"
