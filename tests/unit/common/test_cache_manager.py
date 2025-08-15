"""Unit tests for cache_manager module."""

from eligibility_signposting_api.common.cache_manager import (
    FLASK_APP_CACHE_KEY,
    cache_manager,
)


class TestCacheManager:
    """Test the cache manager functionality."""

    def setup_method(self):
        """Clean up cache before each test."""
        cache_manager.clear_all()

    def test_set_and_get_cache(self):
        """Test basic cache set and get operations."""
        test_key = "test_key"
        test_value = "test_value"

        # Set cache
        cache_manager.set(test_key, test_value)

        # Get cache
        result = cache_manager.get(test_key)
        assert result == test_value

    def test_get_cache_nonexistent_key(self):
        """Test getting a non-existent cache key returns None."""
        result = cache_manager.get("non_existent_key")
        assert result is None

    def test_clear_cache_existing_key(self):
        """Test clearing an existing cache key."""
        test_key = "test_key"
        test_value = "test_value"

        cache_manager.set(test_key, test_value)
        assert cache_manager.get(test_key) == test_value

        # Clear cache
        result = cache_manager.clear(test_key)
        assert result is True  # Should return True if key existed
        assert cache_manager.get(test_key) is None

    def test_clear_cache_nonexistent_key(self):
        """Test clearing a non-existent cache key."""
        # This should not raise an exception
        result = cache_manager.clear("non_existent_key")
        assert result is False  # Should return False if key didn't exist

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.set("key3", "value3")

        # Verify keys exist
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") == "value2"
        assert cache_manager.get("key3") == "value3"

        # Clear all caches
        cache_manager.clear_all()

        # Verify all keys are gone
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
        assert cache_manager.get("key3") is None

    def test_get_cache_info_with_len_objects(self):
        """Test cache info with objects that have __len__."""
        test_list = [1, 2, 3, 4, 5]
        test_dict = {"a": 1, "b": 2, "c": 3}

        cache_manager.set("list_key", test_list)
        cache_manager.set("dict_key", test_dict)

        cache_info = cache_manager.get_cache_info()
        assert cache_info["list_key"] == len(test_list)
        assert cache_info["dict_key"] == len(test_dict)

    def test_get_cache_info_with_non_len_objects(self):
        """Test cache info with objects that don't have __len__."""
        test_int = 42
        test_str = "test"
        expected_int_size = 1  # Default for non-len objects

        cache_manager.set("int_key", test_int)
        cache_manager.set("str_key", test_str)

        cache_info = cache_manager.get_cache_info()
        assert cache_info["int_key"] == expected_int_size  # Default for non-len objects
        assert cache_info["str_key"] == len(test_str)

    def test_flask_app_cache_key_constant(self):
        """Test that the Flask app cache key constant is available."""
        assert FLASK_APP_CACHE_KEY == "flask_app"

    def test_cache_overwrites_existing_value(self):
        """Test that setting a cache key overwrites existing value."""
        cache_manager.set("key", "original_value")
        assert cache_manager.get("key") == "original_value"

        cache_manager.set("key", "new_value")
        assert cache_manager.get("key") == "new_value"

    def test_cache_info_empty_cache(self):
        """Test cache info when cache is empty."""
        cache_info = cache_manager.get_cache_info()
        assert cache_info == {}

    def test_cache_handles_none_values(self):
        """Test that cache can handle None values."""
        cache_manager.set("none_key", None)
        result = cache_manager.get("none_key")
        assert result is None

        # Verify the key actually exists (not just returning None for missing key)
        assert cache_manager.has("none_key") is True

    def test_has_method(self):
        """Test the has() method."""
        assert cache_manager.has("nonexistent") is False

        cache_manager.set("test_key", "test_value")
        assert cache_manager.has("test_key") is True

        cache_manager.clear("test_key")
        assert cache_manager.has("test_key") is False

    def test_size_method(self):
        """Test the size() method."""
        empty_cache_size = 0
        single_item_size = 1
        two_items_size = 2

        assert cache_manager.size() == empty_cache_size

        cache_manager.set("key1", "value1")
        assert cache_manager.size() == single_item_size

        cache_manager.set("key2", "value2")
        assert cache_manager.size() == two_items_size

        cache_manager.clear("key1")
        assert cache_manager.size() == single_item_size

        cache_manager.clear_all()
        assert cache_manager.size() == empty_cache_size
