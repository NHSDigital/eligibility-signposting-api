import logging
import operator
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar, cast

from dateutil.relativedelta import relativedelta
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description

from eligibility_signposting_api.model.campaign_config import RuleOperator

logger = logging.getLogger(__name__)


@dataclass
class Operator(BaseMatcher[str | None], ABC):
    """An operator compares some person's data attribute - date of birth, postcode, flags or so on - against a value
    specified in a rule."""

    ITEM_DEFAULT_PATTERN: ClassVar[str] = r"(?P<rule_value>[^\[]+)\[\[NVL:(?P<item_default>[^\]]+)\]\]"

    rule_value: str
    item_default: str | None = None

    def __post_init__(self) -> None:
        if self.rule_value and (match := re.fullmatch(self.ITEM_DEFAULT_PATTERN, self.rule_value)):
            self.rule_value = match.group("rule_value")
            self.item_default = match.group("item_default")

    @abstractmethod
    def _matches(self, item: str | None) -> bool: ...

    def describe_to(self, description: Description) -> None:
        description.append_text(f"need {self.rule_value} matching: {self.__class__.__name__}")


class OperatorRegistry:
    """Operators are registered and made available for retrieval here for each RuleOperator."""

    registry: ClassVar[dict[RuleOperator, type[Operator]]] = {}

    @staticmethod
    def register(rule_operator: RuleOperator) -> Callable[[type[Operator]], type[Operator]]:
        def decorator(clazz: type[Operator]) -> type[Operator]:
            OperatorRegistry.registry[rule_operator] = clazz
            return clazz

        return decorator

    @staticmethod
    def get(rule_operator: RuleOperator) -> type[Operator]:
        if clazz := OperatorRegistry.registry.get(rule_operator):
            return clazz
        msg = f"{rule_operator} not implemented"
        raise NotImplementedError(msg)


class ScalarOperator(Operator, ABC):
    comparator: ClassVar[Callable[[str | None, str | None], bool]]

    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        data_comparator = cast("Callable[[str|int, str|int], bool]", self.comparator)

        if item is None:
            return self.matches_none()

        if item == "":
            # If item is an empty string, only EQ and NE can match
            return self.comparator in (operator.eq, operator.ne) and data_comparator(item, self.rule_value)

        person_data, rule_value = self.coerce_types(item, self.rule_value)
        return data_comparator(person_data, rule_value)

    def coerce_types(self, left: str, right: str) -> tuple[str | int, str | int]:
        if all(self.int_like(i) for i in (left, right)):
            # If both sides can be treated as numeric, do so.
            return int(left), int(right)
        # Treat both sides as strings.
        return left, right

    def matches_none(self) -> bool:
        match self.comparator:
            case operator.eq:
                # For an EQ comparison, match falsy things except the empty string.
                return not bool(self.rule_value) and self.rule_value != ""
            case operator.ne:
                # For an NE comparison, match truthy things and the empty string.
                return bool(self.rule_value) or self.rule_value == ""
            case _:
                # For anything other than EQ or NE comparisons, a None won't match.
                return False

    @staticmethod
    def int_like(val: str) -> bool:
        return isinstance(val, str) and bool(re.fullmatch(r"-?\d+$", val))

    def describe_to(self, description: Description) -> None:
        description.append_text(f"need {self.__class__.__name__} (item {self.comparator.__name__} {self.rule_value})")


SCALAR_OPERATORS = [
    (RuleOperator.equals, operator.eq),
    (RuleOperator.ne, operator.ne),
    (RuleOperator.gt, operator.gt),
    (RuleOperator.gte, operator.ge),
    (RuleOperator.lt, operator.lt),
    (RuleOperator.lte, operator.le),
]

for rule_operator, comparator in SCALAR_OPERATORS:
    OperatorRegistry.register(rule_operator)(
        cast(
            "type[Operator]",
            type(
                f"_{rule_operator.name}",
                (ScalarOperator,),
                {"comparator": staticmethod(comparator), "__module__": __name__},
            ),
        )
    )


@OperatorRegistry.register(RuleOperator.contains)
class Contains(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        return bool(item) and self.rule_value in str(item)


@OperatorRegistry.register(RuleOperator.not_contains)
class NotContains(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        return self.rule_value not in str(item)


@OperatorRegistry.register(RuleOperator.starts_with)
class StartsWith(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        return str(item).startswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.not_starts_with)
class NotStartsWith(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        return not str(item).startswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.ends_with)
class EndsWith(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        return str(item).endswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.is_in)
@OperatorRegistry.register(RuleOperator.member_of)
class IsIn(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        comparators = set(str(self.rule_value).split(","))
        items = set(str(item).split(","))
        return bool(items & comparators)


@OperatorRegistry.register(RuleOperator.not_in)
@OperatorRegistry.register(RuleOperator.not_member_of)
class NotIn(Operator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        comparators = set(str(self.rule_value).split(","))
        items = set(str(item).split(","))
        return not bool(items & comparators)


@OperatorRegistry.register(RuleOperator.is_null)
class IsNull(Operator):
    def _matches(self, item: str | None) -> bool:
        return item in (None, "")


@OperatorRegistry.register(RuleOperator.is_not_null)
class IsNotNull(Operator):
    def _matches(self, item: str | None) -> bool:
        return item not in (None, "")


class RangeOperator(Operator, ABC):
    low_comparator: int
    high_comparator: int

    def __post_init__(self) -> None:
        super().__post_init__()

        low_comparator_str, high_comparator_str = str(self.rule_value).split(",")
        self.low_comparator = min(int(low_comparator_str), int(high_comparator_str))
        self.high_comparator = max(int(low_comparator_str), int(high_comparator_str))


@OperatorRegistry.register(RuleOperator.is_between)
class Between(RangeOperator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        if item in (None, ""):
            return False
        return self.low_comparator <= int(item) <= self.high_comparator


@OperatorRegistry.register(RuleOperator.is_not_between)
class NotBetween(RangeOperator):
    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        if item in (None, ""):
            return False
        return not self.low_comparator <= int(item) <= self.high_comparator


@OperatorRegistry.register(RuleOperator.is_empty)
class IsEmpty(Operator):
    def _matches(self, item: str | None) -> bool:
        return item is None or not item


@OperatorRegistry.register(RuleOperator.is_not_empty)
class IsNotEmpty(Operator):
    def _matches(self, item: str | None) -> bool:
        return item is not None and bool(item)


@OperatorRegistry.register(RuleOperator.is_true)
class IsTrue(Operator):
    def _matches(self, item: str | None) -> bool:
        return item is True


@OperatorRegistry.register(RuleOperator.is_false)
class IsFalse(Operator):
    def _matches(self, item: str | None) -> bool:
        return item is False


class DateOperator(Operator, ABC):
    OFFSET_PATTERN: ClassVar[str] = r"(?P<rule_value>[^\[]+)\[\[OFFSET:(?P<offset>\d{8})\]\]"
    delta_type: ClassVar[str]
    comparator: ClassVar[Callable[[date, date], bool]]
    offset: date | None = None

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.rule_value and (match := re.fullmatch(self.OFFSET_PATTERN, self.rule_value)):
            self.rule_value = match.group("rule_value")
            self.offset = datetime.strptime(match.group("offset"), "%Y%m%d").replace(tzinfo=UTC).date()

    @property
    def today(self) -> date:
        return datetime.now(tz=UTC).date()

    @staticmethod
    def get_attribute_date(item: str | None) -> date | None:
        return datetime.strptime(str(item), "%Y%m%d").replace(tzinfo=UTC).date() if item else None

    @property
    def cutoff(self) -> date:
        delta = relativedelta()
        setattr(delta, self.delta_type, int(self.rule_value))
        return (self.offset if self.offset else self.today) + delta

    def _matches(self, item: str | None) -> bool:
        item = item if item is not None else self.item_default
        if attribute_date := self.get_attribute_date(item):
            date_comparator = cast("Callable[[date, date], bool]", self.comparator)
            return date_comparator(attribute_date, self.cutoff)
        return False

    def describe_to(self, description: Description) -> None:
        description.append_text(
            f"{self.__class__.__name__} "
            f"(attribute_date {self.comparator.__name__} today + {self.rule_value} {self.delta_type})"
        )


DATE_OPERATORS = [
    (RuleOperator.day_lte, "days", operator.le),
    (RuleOperator.day_lt, "days", operator.lt),
    (RuleOperator.day_gte, "days", operator.ge),
    (RuleOperator.day_gt, "days", operator.gt),
    (RuleOperator.week_lte, "weeks", operator.le),
    (RuleOperator.week_lt, "weeks", operator.lt),
    (RuleOperator.week_gte, "weeks", operator.ge),
    (RuleOperator.week_gt, "weeks", operator.gt),
    (RuleOperator.year_lte, "years", operator.le),
    (RuleOperator.year_lt, "years", operator.lt),
    (RuleOperator.year_gte, "years", operator.ge),
    (RuleOperator.year_gt, "years", operator.gt),
]

for rule_operator, delta_type, comparator in DATE_OPERATORS:
    OperatorRegistry.register(rule_operator)(
        cast(
            "type[Operator]",
            type(
                f"_{rule_operator.name}",
                (DateOperator,),
                {"delta_type": delta_type, "comparator": comparator, "__module__": __name__},
            ),
        )
    )
