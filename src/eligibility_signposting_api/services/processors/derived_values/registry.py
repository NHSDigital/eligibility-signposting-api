from typing import ClassVar

from eligibility_signposting_api.services.processors.derived_values.base import (
    DerivedValueContext,
    DerivedValueHandler,
)


class DerivedValueRegistry:
    """Registry for derived value handlers.

    This class manages the registration and lookup of derived value handlers.
    It provides a centralized way to:
    - Register new derived value handlers
    - Look up handlers by function name
    - Check if an attribute is a derived value

    Example usage:
        registry = DerivedValueRegistry()
        registry.register(AddDaysHandler(default_days=91))

        # Check if a token uses a derived value
        if registry.has_handler("ADD_DAYS"):
            handler = registry.get_handler("ADD_DAYS")
            result = handler.calculate(context)
    """

    # Class-level default handlers - these can be configured at startup
    _default_handlers: ClassVar[dict[str, DerivedValueHandler]] = {}

    def __init__(self) -> None:
        """Initialize the registry with default handlers."""
        self._handlers: dict[str, DerivedValueHandler] = {}
        # Copy default handlers to instance
        for name, handler in self._default_handlers.items():
            self._handlers[name] = handler

    @classmethod
    def register_default(cls, handler: DerivedValueHandler) -> None:
        """Register a handler as a default for all registry instances.

        This is useful for configuring handlers at application startup.

        Args:
            handler: The derived value handler to register
        """
        cls._default_handlers[handler.function_name] = handler

    @classmethod
    def clear_defaults(cls) -> None:
        """Clear all default handlers. Useful for testing."""
        cls._default_handlers.clear()

    @classmethod
    def get_default_handlers(cls) -> dict[str, DerivedValueHandler]:
        """Get a copy of the default handlers. Useful for testing."""
        return cls._default_handlers.copy()

    @classmethod
    def set_default_handlers(cls, handlers: dict[str, DerivedValueHandler]) -> None:
        """Set the default handlers. Useful for testing."""
        cls._default_handlers = handlers

    def register(self, handler: DerivedValueHandler) -> None:
        """Register a derived value handler.

        Args:
            handler: The handler to register. Its function_name attribute
                    will be used as the lookup key.
        """
        self._handlers[handler.function_name] = handler

    def get_handler(self, function_name: str) -> DerivedValueHandler | None:
        """Get a handler by function name.

        Args:
            function_name: The function name (e.g., 'ADD_DAYS')

        Returns:
            The handler or None if not found
        """
        return self._handlers.get(function_name.upper())

    def has_handler(self, function_name: str) -> bool:
        """Check if a handler exists for a function name.

        Args:
            function_name: The function name to check

        Returns:
            True if a handler is registered
        """
        return function_name.upper() in self._handlers

    def is_derived_attribute(self, attribute_value: str) -> bool:
        """Check if an attribute value represents a derived attribute.

        This checks across all registered handlers.

        Args:
            attribute_value: The attribute to check (e.g., 'NEXT_DOSE_DUE')

        Returns:
            True if any handler can derive this attribute
        """
        for handler in self._handlers.values():
            # Pass None for function_args as we're just checking capability
            source = handler.get_source_attribute(attribute_value, function_args=None)
            if source != attribute_value:
                return True
        return False

    def get_source_attribute(self, function_name: str, target_attribute: str, function_args: str | None = None) -> str:
        """Get the source attribute for a derived attribute.

        Args:
            function_name: The function name of the handler
            target_attribute: The target derived attribute
            function_args: Optional arguments from the token function call

        Returns:
            The source attribute name, or the target if no handler found
        """
        handler = self.get_handler(function_name)
        if handler:
            return handler.get_source_attribute(target_attribute, function_args)
        return target_attribute

    def calculate(
        self,
        function_name: str,
        context: DerivedValueContext,
    ) -> str:
        """Calculate a derived value.

        Args:
            function_name: The function name (e.g., 'ADD_DAYS')
            context: The context containing all data needed for calculation

        Returns:
            The calculated value as a string

        Raises:
            ValueError: If no handler found for the function name
        """
        handler = self.get_handler(function_name)
        if not handler:
            message = f"No handler registered for function: {function_name}"
            raise ValueError(message)

        return handler.calculate(context)


# Create a singleton instance for convenience
_registry = DerivedValueRegistry()


def get_registry() -> DerivedValueRegistry:
    """Get the global derived value registry.

    Returns:
        The singleton DerivedValueRegistry instance
    """
    return _registry
