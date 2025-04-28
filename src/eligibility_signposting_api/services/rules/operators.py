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

from eligibility_signposting_api.model.rules import RuleOperator

AttributeData = str | None
logger = logging.getLogger(__name__)


@dataclass
class Operator(BaseMatcher[AttributeData], ABC):
    rule_value: str

    @abstractmethod
    def _matches(self, item: AttributeData) -> bool: ...

    def describe_to(self, description: Description) -> None:
        description.append_text(f"need {self.rule_value} matching: {self.__class__.__name__}")


class OperatorRegistry:
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


class ComparisonOperator(Operator, ABC):
    comparator: ClassVar[Callable[[AttributeData, AttributeData], bool]]

    def _matches(self, item: AttributeData) -> bool:
        data_comparator = cast("Callable[[str|int, str|int], bool]", self.comparator)
        person_data: str | int
        rule_value: str | int
        if not item or not self.rule_value:
            return False
        if re.match(r"-?\d+$", item) and re.match(r"-?\d+$", self.rule_value):
            person_data, rule_value = int(item), int(self.rule_value)
        else:
            person_data, rule_value = str(item), str(self.rule_value)
        return data_comparator(person_data, rule_value)

    def describe_to(self, description: Description) -> None:
        description.append_text(f"{self.__class__.__name__} (item {self.comparator.__name__} {self.rule_value})")


COMPARISON_OPERATORS = [
    (RuleOperator.equals, operator.eq),
    (RuleOperator.ne, operator.ne),
    (RuleOperator.gt, operator.gt),
    (RuleOperator.gte, operator.ge),
    (RuleOperator.lt, operator.lt),
    (RuleOperator.lte, operator.le),
]

for rule_operator, comparator in COMPARISON_OPERATORS:
    OperatorRegistry.register(rule_operator)(
        type(
            f"_{rule_operator.name}",
            (ComparisonOperator,),
            {"comparator": staticmethod(comparator), "__module__": __name__},
        )
    )


@OperatorRegistry.register(RuleOperator.contains)
class Contains(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return bool(item) and self.rule_value in str(item)


@OperatorRegistry.register(RuleOperator.not_contains)
class NotContains(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return self.rule_value not in str(item)


@OperatorRegistry.register(RuleOperator.starts_with)
class StartsWith(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return str(item).startswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.not_starts_with)
class NotStartsWith(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return not str(item).startswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.ends_with)
class EndsWith(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return str(item).endswith(self.rule_value)


@OperatorRegistry.register(RuleOperator.is_in)
class IsIn(Operator):
    def _matches(self, item: AttributeData) -> bool:
        comparators = str(self.rule_value).split(",")
        return str(item) in comparators


@OperatorRegistry.register(RuleOperator.not_in)
class NotIn(Operator):
    def _matches(self, item: AttributeData) -> bool:
        comparators = str(self.rule_value).split(",")
        return str(item) not in comparators


@OperatorRegistry.register(RuleOperator.member_of)
class MemberOf(Operator):
    def _matches(self, item: AttributeData) -> bool:
        attribute_values = str(item).split(",")
        return self.rule_value in attribute_values


@OperatorRegistry.register(RuleOperator.not_member_of)
class NotMemberOf(Operator):
    def _matches(self, item: AttributeData) -> bool:
        attribute_values = str(item).split(",")
        return self.rule_value not in attribute_values


@OperatorRegistry.register(RuleOperator.is_null)
class IsNull(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item in (None, "")


@OperatorRegistry.register(RuleOperator.is_not_null)
class IsNotNull(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item not in (None, "")


class RangeOperator(Operator, ABC):
    def __init__(self, rule_value: str) -> None:
        super().__init__(rule_value=rule_value)
        low_comparator_str, high_comparator_str = str(self.rule_value).split(",")
        self.low_comparator = min(int(low_comparator_str), int(high_comparator_str))
        self.high_comparator = max(int(low_comparator_str), int(high_comparator_str))


@OperatorRegistry.register(RuleOperator.between)
class Between(RangeOperator):
    def _matches(self, item: AttributeData) -> bool:
        if item in (None, ""):
            return False
        return self.low_comparator <= int(item) <= self.high_comparator


@OperatorRegistry.register(RuleOperator.not_between)
class NotBetween(RangeOperator):
    def _matches(self, item: AttributeData) -> bool:
        if item in (None, ""):
            return False
        return not self.low_comparator <= int(item) <= self.high_comparator


@OperatorRegistry.register(RuleOperator.is_empty)
class IsEmpty(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item is None or all(item.strip() == "" for item in str(item).split(","))


@OperatorRegistry.register(RuleOperator.is_not_empty)
class IsNotEmpty(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item is not None and any(item.strip() != "" for item in str(item).split(","))


@OperatorRegistry.register(RuleOperator.is_true)
class IsTrue(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item is True


@OperatorRegistry.register(RuleOperator.is_false)
class IsFalse(Operator):
    def _matches(self, item: AttributeData) -> bool:
        return item is False


class DateOperator(Operator, ABC):
    delta_type: ClassVar[str]
    comparator: ClassVar[Callable[[date, date], bool]]

    @property
    def today(self) -> date:
        return datetime.now(tz=UTC).date()

    @staticmethod
    def get_attribute_date(item: AttributeData) -> date | None:
        return datetime.strptime(str(item), "%Y%m%d").replace(tzinfo=UTC).date() if item else None

    @property
    def cutoff(self) -> date:
        delta = relativedelta()
        setattr(delta, self.delta_type, int(self.rule_value))
        return self.today + delta

    def _matches(self, item: AttributeData) -> bool:
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
