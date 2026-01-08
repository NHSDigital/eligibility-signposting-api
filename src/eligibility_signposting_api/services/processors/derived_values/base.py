from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class DerivedValueContext:
    """Context object containing all data needed for derived value calculation.

    Attributes:
        person_data: List of person attribute dictionaries
        attribute_name: The condition/vaccine type (e.g., 'COVID', 'RSV')
        source_attribute: The source attribute to derive from (e.g., 'LAST_SUCCESSFUL_DATE')
        function_args: Arguments passed to the function (e.g., number of days)
        date_format: Optional date format string for output formatting
    """

    person_data: list[dict[str, Any]]
    attribute_name: str
    source_attribute: str | None
    function_args: str | None
    date_format: str | None


class DerivedValueHandler(ABC):
    """Abstract base class for derived value handlers.

    Derived value handlers compute values that don't exist directly in the data
    but are calculated from existing attributes. Each handler is responsible for
    a specific type of calculation (e.g., adding days to a date).

    To create a new derived value handler:
    1. Subclass DerivedValueHandler
    2. Set the `function_name` class attribute to the token function name (e.g., 'ADD_DAYS')
    3. Implement the `calculate` method
    4. Register the handler with the DerivedValueRegistry
    """

    function_name: str = ""

    @abstractmethod
    def calculate(self, context: DerivedValueContext) -> str:
        """Calculate the derived value.

        Args:
            context: DerivedValueContext containing all necessary data

        Returns:
            The calculated value as a string

        Raises:
            ValueError: If the calculation cannot be performed
        """

    @abstractmethod
    def get_source_attribute(self, target_attribute: str) -> str:
        """Get the source attribute name needed for this derived value.

        For example, NEXT_DOSE_DUE derives from LAST_SUCCESSFUL_DATE.

        Args:
            target_attribute: The target derived attribute name (e.g., 'NEXT_DOSE_DUE')

        Returns:
            The source attribute name to use for calculation
        """
