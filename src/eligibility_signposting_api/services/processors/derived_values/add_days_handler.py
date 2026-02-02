from datetime import UTC, datetime, timedelta
from typing import ClassVar

from eligibility_signposting_api.services.processors.derived_values.base import (
    DerivedValueContext,
    DerivedValueHandler,
)


class AddDaysHandler(DerivedValueHandler):
    """Handler for adding days to a date value.

    This handler calculates derived dates by adding a configurable number of days
    to a source date attribute. It supports:
    - Default days value for all vaccine types
    - Vaccine-specific days configuration
    - Configurable mapping of derived attributes to source attributes

    Example token: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]
    This would add 91 days to COVID's LAST_SUCCESSFUL_DATE to calculate NEXT_DOSE_DUE.

    The number of days can be specified in three ways (in order of precedence):
    1. In the token itself: :ADD_DAYS(91)
    2. In the vaccine_type_days configuration
    3. Using the default_days value
    """

    function_name: str = "ADD_DAYS"

    DERIVED_ATTRIBUTE_SOURCES: ClassVar[dict[str, str]] = {
        "NEXT_DOSE_DUE": "LAST_SUCCESSFUL_DATE",
    }

    def __init__(
        self,
        default_days: int = 91,
        vaccine_type_days: dict[str, int] | None = None,
    ) -> None:
        """Initialize the AddDaysHandler.

        Args:
            default_days: Default number of days to add when not specified
                        in token or vaccine_type_days. Defaults to 91.
            vaccine_type_days: Dictionary mapping vaccine types to their
                        specific days values. E.g., {"COVID": 91, "FLU": 365}
        """
        self.default_days = default_days
        self.vaccine_type_days = vaccine_type_days or {}

    def get_source_attribute(self, target_attribute: str, function_args: str | None = None) -> str:
        """Get the source attribute for a derived attribute.

        Check if source is provided in function args (e.g., ADD_DAYS(91, SOURCE_FIELD)).
        If not, fall back to mapping or return target_attribute as default.

        Args:
            target_attribute: The derived attribute name (e.g., 'NEXT_DOSE_DUE')
            function_args: Optional arguments from token (e.g., '91, LAST_SUCCESSFUL_DATE')

        Returns:
            The source attribute name (e.g., 'LAST_SUCCESSFUL_DATE')
        """
        if function_args and "," in function_args:
            parts = [p.strip() for p in function_args.split(",")]
            if len(parts) > 1 and parts[1]:
                return parts[1].upper()

        return self.DERIVED_ATTRIBUTE_SOURCES.get(target_attribute, target_attribute)

    def calculate(self, context: DerivedValueContext) -> str:
        """Calculate a date with added days.

        Args:
            context: DerivedValueContext containing:
                - person_data: List of attribute dictionaries
                - attribute_name: Vaccine type (e.g., 'COVID')
                - source_attribute: The source date attribute
                - function_args: Optional days override from token
                - date_format: Optional output date format

        Returns:
            The calculated date as a formatted string

        Raises:
            ValueError: If source date is not found or invalid
        """
        source_date = self._find_source_date(context)
        if not source_date:
            return ""

        days_to_add = self._get_days_to_add(context)
        calculated_date = self._add_days_to_date(source_date, days_to_add)

        return self._format_date(calculated_date, context.date_format)

    def _find_source_date(self, context: DerivedValueContext) -> str | None:
        """Find the source date value from person data.

        For PERSON/COHORT-level attributes, looks for ATTRIBUTE_TYPE == attribute_level.
        For TARGET-level attributes, looks for ATTRIBUTE_TYPE == context.attribute_name (e.g., "COVID").

        Args:
            context: The derived value context

        Returns:
            The source date string or None if not found
        """
        source_attr = context.source_attribute
        if not source_attr:
            return None

        if context.attribute_level in ("PERSON", "COHORT"):
            attribute_type_to_match = context.attribute_level
        else:
            attribute_type_to_match = context.attribute_name

        for attribute in context.person_data:
            if attribute.get("ATTRIBUTE_TYPE") == attribute_type_to_match:
                return attribute.get(source_attr)

        return None

    def _get_days_to_add(self, context: DerivedValueContext) -> int:
        """Determine the number of days to add.

        Priority:
        1. Function argument from token (e.g., :ADD_DAYS(91))
        2. Vaccine-specific configuration
        3. Default days

        Args:
            context: The derived value context

        Returns:
            Number of days to add
        """
        if context.function_args:
            args = context.function_args.split(",")[0].strip()
            if args:
                try:
                    return int(args)
                except ValueError as e:
                    message = f"Invalid days argument '{args}' for ADD_DAYS function. Expected an integer."
                    raise ValueError(message) from e

        if context.attribute_name in self.vaccine_type_days:
            return self.vaccine_type_days[context.attribute_name]

        return self.default_days

    def _add_days_to_date(self, date_str: str, days: int) -> datetime:
        """Parse a date string and add days.

        Args:
            date_str: Date in YYYYMMDD format
            days: Number of days to add

        Returns:
            The calculated datetime

        Raises:
            ValueError: If date format is invalid
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC)
            return date_obj + timedelta(days=days)
        except ValueError as e:
            message = f"Invalid date format: {date_str}"
            raise ValueError(message) from e

    def _format_date(self, date_obj: datetime, date_format: str | None) -> str:
        """Format a datetime object.

        Args:
            date_obj: The datetime to format
            date_format: Optional strftime format string

        Returns:
            Formatted date string. If no format specified, returns YYYYMMDD.
        """
        if date_format:
            return date_obj.strftime(date_format)
        return date_obj.strftime("%Y%m%d")
