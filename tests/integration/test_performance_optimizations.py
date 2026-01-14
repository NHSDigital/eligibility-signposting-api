#TODO needs migration to fargate
# """
# Test to verify the performance optimization caching is working correctly.
# """
#
# from eligibility_signposting_api.app import get_or_create_app
# from eligibility_signposting_api.common.cache_manager import (
#     FLASK_APP_CACHE_KEY,
#     cache_manager,
# )
#
#
# class TestPerformanceOptimizations:
#     """Tests to verify caching optimizations work correctly."""
#
#     def test_flask_app_caching(self):
#         """Test that Flask app is cached and reused."""
#         # Clear all caches first
#         cache_manager.clear_all()
#
#         # First call should create and cache the app
#         app1 = get_or_create_app()
#         cache_info_after_first = cache_manager.get_cache_info()
#
#         # Second call should reuse the cached app
#         app2 = get_or_create_app()
#         cache_info_after_second = cache_manager.get_cache_info()
#
#         # Verify same instance is returned
#         assert app1 is app2, "Flask app should be reused from cache"
#
#         # Verify cache contains the Flask app
#         assert FLASK_APP_CACHE_KEY in cache_info_after_first
#         assert FLASK_APP_CACHE_KEY in cache_info_after_second
#
#         # Cache info should be the same after second call (no new caching)
#         assert cache_info_after_first == cache_info_after_second
#
#     def test_cache_clearing_works(self):
#         """Test that cache clearing functionality works."""
#         # Set up some cached data
#         app1 = get_or_create_app()
#         cache_info_before = cache_manager.get_cache_info()
#
#         # Verify cache has data
#         assert len(cache_info_before) > 0, "Cache should contain Flask app"
#
#         # Clear all caches
#         cache_manager.clear_all()
#         cache_info_after = cache_manager.get_cache_info()
#
#         # Verify cache is empty
#         assert len(cache_info_after) == 0, "Cache should be empty after clearing"
#
#         # New app should be different instance
#         app2 = get_or_create_app()
#         assert app1 is not app2, "New Flask app should be created after cache clear"
#
#     def test_automatic_cache_clearing_in_tests(self):
#         """Test that the automatic cache clearing fixture works."""
#         # This test relies on the clear_performance_caches fixture
#         # which should clear caches before each test class
#
#         # We can't guarantee completely empty cache because of test setup,
#         # but we can verify the cache clearing mechanism exists
#
#         # Create some cached data
#         app = get_or_create_app()
#         assert app is not None
#
#         # Verify Flask app is now cached
#         cache_info_after = cache_manager.get_cache_info()
#         assert FLASK_APP_CACHE_KEY in cache_info_after
#
#     def test_clear_cache_specific_key(self):
#         """Test clearing a specific cache key and logging."""
#         # Set up test data
#         test_key = "test_cache_key"
#         test_value = "test_value"
#         cache_manager.set(test_key, test_value)
#
#         # Verify key exists
#         cache_info_before = cache_manager.get_cache_info()
#         assert test_key in cache_info_before
#
#         # Clear specific key (this covers lines 28-29)
#         result = cache_manager.clear(test_key)
#         assert result is True  # Should return True for existing key
#
#         # Verify key is removed
#         cache_info_after = cache_manager.get_cache_info()
#         assert test_key not in cache_info_after
#
#         # Clearing non-existent key should not cause error
#         result = cache_manager.clear("non_existent_key")
#         assert result is False  # Should return False for non-existent key
#
#     def test_cache_info_with_non_len_objects(self):
#         """Test get_cache_info with objects that don't have __len__ method."""
#
#         # Set up object that raises TypeError on len() (covers lines 44-45)
#         class NoLenObject:
#             def __len__(self):
#                 msg = "This object doesn't support len()"
#                 raise TypeError(msg)
#
#         test_key = "no_len_object"
#         no_len_obj = NoLenObject()
#         cache_manager.set(test_key, no_len_obj)
#
#         # This should handle the TypeError gracefully
#         cache_info = cache_manager.get_cache_info()
#         assert test_key in cache_info
#         assert cache_info[test_key] == 1  # Should default to 1
