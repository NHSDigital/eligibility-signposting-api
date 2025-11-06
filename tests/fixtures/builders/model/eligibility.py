import random
import string

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import (
    RuleName,
    RulePriority,
    RuleText,
    RuleType,
    UrlLink,
)


class SuggestedActionFactory(DataclassFactory[eligibility_status.SuggestedAction]):
    url_link = UrlLink("https://test-example.com")


class ReasonFactory(DataclassFactory[eligibility_status.Reason]):
    rule_type = RuleType.filter
    rule_name = RuleName("name")
    rule_code = RuleName("code")
    rule_priority = RulePriority("1")
    rule_text = RuleText("text")
    matcher_matched = False


class CohortResultFactory(DataclassFactory[eligibility_status.CohortGroupResult]):
    reasons = Use(ReasonFactory.batch, size=2)


class ConditionFactory(DataclassFactory[eligibility_status.Condition]):
    actions = Use(SuggestedActionFactory.batch, size=2)
    cohort_results = Use(CohortResultFactory.batch, size=2)
    suitability_rules = Use(ReasonFactory.batch, size=2)


class EligibilityStatusFactory(DataclassFactory[eligibility_status.EligibilityStatus]):
    conditions = Use(ConditionFactory.batch, size=2)


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
