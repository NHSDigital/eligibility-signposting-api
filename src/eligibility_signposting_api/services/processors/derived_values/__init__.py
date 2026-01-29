from eligibility_signposting_api.services.processors.derived_values.add_days_handler import AddDaysHandler
from eligibility_signposting_api.services.processors.derived_values.base import (
    DerivedValueContext,
    DerivedValueHandler,
)
from eligibility_signposting_api.services.processors.derived_values.registry import (
    DerivedValueRegistry,
    get_registry,
)

__all__ = [
    "AddDaysHandler",
    "DerivedValueContext",
    "DerivedValueHandler",
    "DerivedValueRegistry",
    "get_registry",
]

# Register default handlers
DerivedValueRegistry.register_default(
    AddDaysHandler(
        default_days=91,
        vaccine_type_days={
            "COVID": 91,  # 91 days between COVID vaccinations
            # Add other vaccine-specific configurations here as needed.
        },
    )
)
