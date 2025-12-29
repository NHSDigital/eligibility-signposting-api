from unittest.mock import MagicMock

import pytest

from eligibility_signposting_api.services.processors.derived_values import (
    AddDaysHandler,
    DerivedValueContext,
    DerivedValueRegistry,
)


class TestAddDaysHandler:
    """Tests for the AddDaysHandler class."""

    def test_calculate_adds_default_days_to_date(self):
        """Test that calculate adds the default days to a date."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 91 days = 2025-04-02
        assert result == "20250402"

    def test_calculate_with_function_args_override(self):
        """Test that function args override default days."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args="30",  # Override with 30 days
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 30 days = 2025-01-31
        assert result == "20250131"

    def test_calculate_with_vaccine_specific_days(self):
        """Test that vaccine-specific days are used when configured."""
        handler = AddDaysHandler(
            default_days=91,
            vaccine_type_days={"FLU": 365},
        )
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "FLU", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="FLU",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 365 days = 2026-01-01
        assert result == "20260101"

    def test_calculate_with_date_format(self):
        """Test that date format is applied to output."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format="%d %B %Y",
        )

        result = handler.calculate(context)

        assert result == "02 April 2025"

    def test_calculate_returns_empty_when_source_not_found(self):
        """Test that empty string is returned when source date not found."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID"}],  # No LAST_SUCCESSFUL_DATE
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        result = handler.calculate(context)

        assert result == ""

    def test_calculate_returns_empty_when_vaccine_not_found(self):
        """Test that empty string is returned when vaccine type not found."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "FLU", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",  # Looking for COVID but data has FLU
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        result = handler.calculate(context)

        assert result == ""

    def test_calculate_with_invalid_date_raises_error(self):
        """Test that invalid date format raises ValueError."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "invalid"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        with pytest.raises(ValueError, match="Invalid date format"):
            handler.calculate(context)

    def test_get_source_attribute_maps_derived_to_source(self):
        """Test that get_source_attribute maps derived attributes correctly."""
        handler = AddDaysHandler()

        assert handler.get_source_attribute("NEXT_DOSE_DUE") == "LAST_SUCCESSFUL_DATE"

    def test_get_source_attribute_returns_original_if_not_mapped(self):
        """Test that unmapped attributes return themselves."""
        handler = AddDaysHandler()

        assert handler.get_source_attribute("UNKNOWN_ATTR") == "UNKNOWN_ATTR"

    def test_function_args_priority_over_vaccine_config(self):
        """Test that function args take priority over vaccine-specific config."""
        handler = AddDaysHandler(
            default_days=91,
            vaccine_type_days={"COVID": 120},
        )
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args="30",  # Should take priority over 120
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 30 days = 2025-01-31
        assert result == "20250131"


class TestDerivedValueRegistry:
    """Tests for the DerivedValueRegistry class."""

    def test_register_and_get_handler(self):
        """Test registering and retrieving a handler."""
        registry = DerivedValueRegistry()
        handler = AddDaysHandler()
        registry.register(handler)

        retrieved = registry.get_handler("ADD_DAYS")

        assert retrieved is handler

    def test_get_handler_case_insensitive(self):
        """Test that handler lookup is case insensitive."""
        registry = DerivedValueRegistry()
        handler = AddDaysHandler()
        registry.register(handler)

        assert registry.get_handler("add_days") is handler
        assert registry.get_handler("Add_Days") is handler

    def test_has_handler_returns_true_when_exists(self):
        """Test has_handler returns True for registered handlers."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert registry.has_handler("ADD_DAYS") is True

    def test_has_handler_returns_false_when_not_exists(self):
        """Test has_handler returns False for unregistered handlers."""
        registry = DerivedValueRegistry()

        assert registry.has_handler("UNKNOWN") is False

    def test_calculate_delegates_to_correct_handler(self):
        """Test that calculate delegates to the correct handler."""
        registry = DerivedValueRegistry()

        # Create a mock handler
        mock_handler = MagicMock()
        mock_handler.function_name = "TEST_FUNC"
        mock_handler.calculate.return_value = "mock_result"

        # Register both real and mock handlers
        registry.register(AddDaysHandler(default_days=91))
        registry.register(mock_handler)

        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        # Call with the mock handler's function name
        result = registry.calculate(function_name="TEST_FUNC", context=context)

        # Verify the mock handler was called with the context
        mock_handler.calculate.assert_called_once_with(context)
        assert result == "mock_result"

    def test_calculate_raises_for_unknown_function(self):
        """Test that calculate raises ValueError for unknown functions."""
        registry = DerivedValueRegistry()

        context = DerivedValueContext(
            person_data=[],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=None,
            date_format=None,
        )

        with pytest.raises(ValueError, match="No handler registered"):
            registry.calculate(
                function_name="UNKNOWN",
                context=context,
            )

    def test_is_derived_attribute_returns_true_for_derived(self):
        """Test is_derived_attribute for known derived attributes."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert registry.is_derived_attribute("NEXT_DOSE_DUE") is True

    def test_is_derived_attribute_returns_false_for_non_derived(self):
        """Test is_derived_attribute for non-derived attributes."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert registry.is_derived_attribute("LAST_SUCCESSFUL_DATE") is False

    def test_default_handlers_are_registered(self):
        """Test that default handlers from the module are registered."""
        registry = DerivedValueRegistry()

        # The default ADD_DAYS handler should be registered via __init__.py
        assert registry.has_handler("ADD_DAYS")

    def test_clear_defaults_removes_default_handlers(self):
        """Test that clear_defaults removes all default handlers."""
        # Save current defaults using public method
        saved_defaults = DerivedValueRegistry.get_default_handlers()

        try:
            DerivedValueRegistry.clear_defaults()

            # New registry should have no handlers
            registry = DerivedValueRegistry()
            assert not registry.has_handler("ADD_DAYS")
        finally:
            # Restore defaults for other tests using public method
            DerivedValueRegistry.set_default_handlers(saved_defaults)
