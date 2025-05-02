import random
import string

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from eligibility_signposting_api.model.eligibility import Condition, EligibilityStatus


class ConditionFactory(DataclassFactory[Condition]): ...


class EligibilityStatusFactory(DataclassFactory[EligibilityStatus]):
    condition = Use(ConditionFactory.batch, size=2)


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))  # noqa: S311
