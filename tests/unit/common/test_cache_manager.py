"""Unit tests for cache_manager module."""

from eligibility_signposting_api.common.cache_manager import (
    FLASK_APP_CACHE_KEY,
    clear_all_caches,
    clear_cache,
    get_cache,
    get_cache_info,
    set_cache,
)


class TestCacheManager:
    """Test the cache manager functionality."""

    def setup_method(self):
        """Clean up cache before each test."""
        clear_all_caches()

    def test_set_and_get_cache(self):
        """Test basic cache set and get operations."""
        test_key = "test_key"
        test_value = "test_value"

        # Set cache
        set_cache(test_key, test_value)

        # Get cache
        result = get_cache(test_key)
        assert result == test_value

    def test_get_cache_nonexistent_key(self):
        """Test getting a non-existent cache key returns None."""
        result = get_cache("non_existent_key")
        assert result is None

    def test_clear_cache_existing_key(self):
        """Test clearing an existing cache key."""
        test_key = "test_key"
        test_value = "test_value"

        # Set cache
        set_cache(test_key, test_value)
        assert get_cache(test_key) == test_value

        # Clear cache
        clear_cache(test_key)
        assert get_cache(test_key) is None

    def test_clear_cache_nonexistent_key(self):
        """Test clearing a non-existent cache key does nothing."""
        # Should not raise an error
        clear_cache("non_existent_key")

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        # Set multiple cache entries
        set_cache("key1", "value1")
        set_cache("key2", "value2")
        set_cache("key3", "value3")

        # Verify they exist
        assert get_cache("key1") == "value1"
        assert get_cache("key2") == "value2"
        assert get_cache("key3") == "value3"

        # Clear all
        clear_all_caches()

        # Verify all are gone
        assert get_cache("key1") is None
        assert get_cache("key2") is None
        assert get_cache("key3") is None

    def test_get_cache_info_with_len_objects(self):
        """Test get_cache_info with objects that have __len__ method."""
        test_list = [1, 2, 3, 4, 5]
        test_dict = {"a": 1, "b": 2}
        test_string = "hello"

        set_cache("list_key", test_list)
        set_cache("dict_key", test_dict)
        set_cache("string_key", test_string)

        cache_info = get_cache_info()

        assert cache_info["list_key"] == len(test_list)
        assert cache_info["dict_key"] == len(test_dict)
        assert cache_info["string_key"] == len(test_string)

    def test_get_cache_info_with_non_len_objects(self):
        """Test get_cache_info with objects that don't support len()."""

        # Object that has __len__ but raises TypeError
        class NoLenObject:
            def __len__(self):
                msg = "This object doesn't support len()"
                raise TypeError(msg)

        # Object without __len__ method
        class NoLenMethodObject:
            pass

        set_cache("no_len_key", NoLenObject())
        set_cache("no_method_key", NoLenMethodObject())
        set_cache("int_key", 42)

        cache_info = get_cache_info()

        # All should default to 1
        assert cache_info["no_len_key"] == 1
        assert cache_info["no_method_key"] == 1
        assert cache_info["int_key"] == 1

    def test_flask_app_cache_key_constant(self):
        """Test that the Flask app cache key constant is available."""
        assert FLASK_APP_CACHE_KEY == "flask_app"

    def test_cache_overwrites_existing_value(self):
        """Test that setting a cache key twice overwrites the previous value."""
        test_key = "test_key"

        set_cache(test_key, "first_value")
        assert get_cache(test_key) == "first_value"

        set_cache(test_key, "second_value")
        assert get_cache(test_key) == "second_value"

    def test_cache_info_empty_cache(self):
        """Test get_cache_info with empty cache."""
        clear_all_caches()
        cache_info = get_cache_info()
        assert cache_info == {}

    def test_cache_handles_none_values(self):
        """Test that cache can store None values."""
        test_key = "none_key"
        set_cache(test_key, None)

        # None should be retrievable
        assert get_cache(test_key) is None

        # Cache info should show it exists
        cache_info = get_cache_info()
        assert test_key in cache_info
