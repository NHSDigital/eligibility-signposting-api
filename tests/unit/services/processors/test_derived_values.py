from unittest.mock import MagicMock

from hamcrest import assert_that, calling, equal_to, is_, raises, same_instance

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
        assert_that(result, is_(equal_to("20250402")))

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
        assert_that(result, is_(equal_to("20250131")))

    def test_get_source_attribute_from_args(self):
        """Test that source attribute is extracted from function args."""
        handler = AddDaysHandler()

        # Test with source attribute provided
        source = handler.get_source_attribute("target", "91, CUSTOM_SOURCE")
        assert_that(source, is_(equal_to("CUSTOM_SOURCE")))

        # Test with only days provided (should fallback to default mapping or target)
        source = handler.get_source_attribute("NEXT_DOSE_DUE", "91")
        assert_that(source, is_(equal_to("LAST_SUCCESSFUL_DATE")))

        # Test with empty args
        source = handler.get_source_attribute("NEXT_DOSE_DUE", None)
        assert_that(source, is_(equal_to("LAST_SUCCESSFUL_DATE")))

    def test_calculate_with_args_source_override(self):
        """Test calculation with source attribute in args."""
        handler = AddDaysHandler(default_days=91)
        # Note: In the real flow, get_source_attribute is called before context creation
        # to set source_attribute in the context. Checking if calculate handles the complex args correctly
        # for days parsing.

        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "CUSTOM_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="CUSTOM_DATE",  # This would have been resolved by get_source_attribute
            function_args="30, CUSTOM_DATE",
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 30 days = 2025-01-31
        assert_that(result, is_(equal_to("20250131")))

    def test_calculate_with_blank_days_and_source_override(self):
        """Test that blank days arg with override falls back to defaults."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args=", LAST_SUCCESSFUL_DATE",
            date_format=None,
        )

        result = handler.calculate(context)

        # No explicit days provided, so default 91 days should be used
        assert_that(result, is_(equal_to("20250402")))

    def test_source_override_trims_whitespace_and_case(self):
        """Test override parsing handles whitespace and lowercase inputs."""
        handler = AddDaysHandler(default_days=91)

        source = handler.get_source_attribute("DOSE_DUE", " 30 , last_successful_date ")
        assert_that(source, is_(equal_to("LAST_SUCCESSFUL_DATE")))

        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute=source,
            function_args=" 30 , last_successful_date ",
            date_format=None,
        )

        result = handler.calculate(context)

        # 2025-01-01 + 30 days = 2025-01-31
        assert_that(result, is_(equal_to("20250131")))

    def test_calculate_with_missing_custom_source_returns_empty(self):
        """Test that missing custom source attribute returns empty string."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID"}],
            attribute_name="COVID",
            source_attribute="CUSTOM_DATE",
            function_args="30, CUSTOM_DATE",
            date_format=None,
        )

        result = handler.calculate(context)

        assert_that(result, is_(equal_to("")))

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
        assert_that(result, is_(equal_to("20260101")))

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

        assert_that(result, is_(equal_to("02 April 2025")))

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

        assert_that(result, is_(equal_to("")))

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

        assert_that(result, is_(equal_to("")))

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

        assert_that(
            calling(handler.calculate).with_args(context),
            raises(ValueError, pattern="Invalid date format"),
        )

    def test_calculate_with_invalid_function_args_raises_error(self):
        """Test that non-integer function args raises ValueError."""
        handler = AddDaysHandler(default_days=91)
        context = DerivedValueContext(
            person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
            attribute_name="COVID",
            source_attribute="LAST_SUCCESSFUL_DATE",
            function_args="abc",  # Invalid: not an integer
            date_format=None,
        )

        assert_that(
            calling(handler.calculate).with_args(context),
            raises(ValueError, pattern="Invalid days argument 'abc' for ADD_DAYS function"),
        )

    def test_get_source_attribute_maps_derived_to_source(self):
        """Test that get_source_attribute maps derived attributes correctly."""
        handler = AddDaysHandler()

        assert_that(handler.get_source_attribute("NEXT_DOSE_DUE"), is_(equal_to("LAST_SUCCESSFUL_DATE")))

    def test_get_source_attribute_returns_original_if_not_mapped(self):
        """Test that unmapped attributes return themselves."""
        handler = AddDaysHandler()

        assert_that(handler.get_source_attribute("UNKNOWN_ATTR"), is_(equal_to("UNKNOWN_ATTR")))

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
        assert_that(result, is_(equal_to("20250131")))


class TestDerivedValueRegistry:
    """Tests for the DerivedValueRegistry class."""

    def test_register_and_get_handler(self):
        """Test registering and retrieving a handler."""
        registry = DerivedValueRegistry()
        handler = AddDaysHandler()
        registry.register(handler)

        retrieved = registry.get_handler("ADD_DAYS")

        assert_that(retrieved, same_instance(handler))  # type: ignore[call-overload]

    def test_get_handler_case_insensitive(self):
        """Test that handler lookup is case insensitive."""
        registry = DerivedValueRegistry()
        handler = AddDaysHandler()
        registry.register(handler)

        assert_that(registry.get_handler("add_days"), same_instance(handler))  # type: ignore[call-overload]
        assert_that(registry.get_handler("Add_Days"), same_instance(handler))  # type: ignore[call-overload]

    def test_has_handler_returns_true_when_exists(self):
        """Test has_handler returns True for registered handlers."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert_that(registry.has_handler("ADD_DAYS"), is_(True))

    def test_has_handler_returns_false_when_not_exists(self):
        """Test has_handler returns False for unregistered handlers."""
        registry = DerivedValueRegistry()

        assert_that(registry.has_handler("UNKNOWN"), is_(False))

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
        assert_that(result, is_(equal_to("mock_result")))

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

        assert_that(
            calling(registry.calculate).with_args(function_name="UNKNOWN", context=context),
            raises(ValueError, pattern="No handler registered"),
        )

    def test_is_derived_attribute_returns_true_for_derived(self):
        """Test is_derived_attribute for known derived attributes."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert_that(registry.is_derived_attribute("NEXT_DOSE_DUE"), is_(True))

    def test_is_derived_attribute_returns_false_for_non_derived(self):
        """Test is_derived_attribute for non-derived attributes."""
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler())

        assert_that(registry.is_derived_attribute("LAST_SUCCESSFUL_DATE"), is_(False))

    def test_default_handlers_are_registered(self):
        """Test that default handlers from the module are registered."""
        registry = DerivedValueRegistry()

        # The default ADD_DAYS handler should be registered via __init__.py
        assert_that(registry.has_handler("ADD_DAYS"), is_(True))

    def test_clear_defaults_removes_default_handlers(self):
        """Test that clear_defaults removes all default handlers."""
        # Save current defaults using public method
        saved_defaults = DerivedValueRegistry.get_default_handlers()

        try:
            DerivedValueRegistry.clear_defaults()

            # New registry should have no handlers
            registry = DerivedValueRegistry()
            assert_that(registry.has_handler("ADD_DAYS"), is_(False))
        finally:
            # Restore defaults for other tests using public method
            DerivedValueRegistry.set_default_handlers(saved_defaults)
