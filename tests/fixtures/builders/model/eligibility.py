import random
import string

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import UrlLink


class SuggestedActionFactory(DataclassFactory[eligibility_status.SuggestedAction]):
    url_link = UrlLink("https://test-example.com")


class ConditionFactory(DataclassFactory[eligibility_status.Condition]):
    actions = Use(SuggestedActionFactory.batch, size=2)


class EligibilityStatusFactory(DataclassFactory[eligibility_status.EligibilityStatus]):
    conditions = Use(ConditionFactory.batch, size=2)


class CohortResultFactory(DataclassFactory[eligibility_status.CohortGroupResult]): ...


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
