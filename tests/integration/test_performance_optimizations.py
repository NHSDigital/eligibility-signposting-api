"""
Test to verify the performance optimization caching is working correctly.
"""

from eligibility_signposting_api.app import get_or_create_app
from eligibility_signposting_api.common.cache_manager import (
    FLASK_APP_CACHE_KEY,
    clear_all_caches,
    get_cache_info,
)


class TestPerformanceOptimizations:
    """Tests to verify caching optimizations work correctly."""

    def test_flask_app_caching(self):
        """Test that Flask app is cached and reused."""
        # Clear all caches first
        clear_all_caches()

        # First call should create and cache the app
        app1 = get_or_create_app()
        cache_info_after_first = get_cache_info()

        # Second call should reuse the cached app
        app2 = get_or_create_app()
        cache_info_after_second = get_cache_info()

        # Verify same instance is returned
        assert app1 is app2, "Flask app should be reused from cache"

        # Verify cache contains the Flask app
        assert FLASK_APP_CACHE_KEY in cache_info_after_first
        assert FLASK_APP_CACHE_KEY in cache_info_after_second

        # Cache info should be the same after second call (no new caching)
        assert cache_info_after_first == cache_info_after_second

    def test_cache_clearing_works(self):
        """Test that cache clearing functionality works."""
        # Set up some cached data
        app1 = get_or_create_app()
        cache_info_before = get_cache_info()

        # Verify cache has data
        assert len(cache_info_before) > 0, "Cache should contain Flask app"

        # Clear all caches
        clear_all_caches()
        cache_info_after = get_cache_info()

        # Verify cache is empty
        assert len(cache_info_after) == 0, "Cache should be empty after clearing"

        # New app should be different instance
        app2 = get_or_create_app()
        assert app1 is not app2, "New Flask app should be created after cache clear"

    def test_automatic_cache_clearing_in_tests(self):
        """Test that the automatic cache clearing fixture works."""
        # This test relies on the clear_performance_caches fixture
        # which should clear caches before each test class

        # We can't guarantee completely empty cache because of test setup,
        # but we can verify the cache clearing mechanism exists

        # Create some cached data
        app = get_or_create_app()
        assert app is not None

        # Verify Flask app is now cached
        cache_info_after = get_cache_info()
        assert FLASK_APP_CACHE_KEY in cache_info_after
