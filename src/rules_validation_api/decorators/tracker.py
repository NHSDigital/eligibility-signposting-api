from typing import Self

from pydantic import model_validator

VALIDATORS_CALLED: list[str] = []


# --- Mixin and decorator to track validators ---
class TrackValidatorsMixin:
    """
    Mixin to track all validator names in a Pydantic model.
    """

    @model_validator(mode="after")
    def _track_validators(self) -> Self:
        for name in dir(self):
            if name.startswith(("validate_", "check_")) and callable(getattr(self, name)):
                full_name = f"{self.__class__.__name__}:{name}"
                if full_name not in VALIDATORS_CALLED:
                    VALIDATORS_CALLED.append(full_name)
        return self


def track_validators(cls) -> type:  # noqa:ANN001
    """
    Decorator to add the tracking mixin to a Pydantic model.
    """
    return type(cls.__name__, (TrackValidatorsMixin, cls), {})
