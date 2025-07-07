import random
import string

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from eligibility_signposting_api.model import eligibility
from eligibility_signposting_api.model.eligibility import UrlLink


class SuggestedActionFactory(DataclassFactory[eligibility.SuggestedAction]):
    url_link = UrlLink("https://test-example.com")


class ConditionFactory(DataclassFactory[eligibility.Condition]):
    actions = Use(SuggestedActionFactory.batch, size=2)


class EligibilityStatusFactory(DataclassFactory[eligibility.EligibilityStatus]):
    conditions = Use(ConditionFactory.batch, size=2)


class CohortResultFactory(DataclassFactory[eligibility.CohortGroupResult]): ...


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
