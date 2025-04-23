from hamcrest.core.matcher import Matcher

from eligibility_signposting_api.model.eligibility import Condition, EligibilityStatus

from .meta import BaseAutoMatcher


class EligibilityStatusMatcher(BaseAutoMatcher[EligibilityStatus]): ...


class ConditionMatcher(BaseAutoMatcher[Condition]): ...


def is_eligibility_status() -> Matcher[EligibilityStatus]:
    return EligibilityStatusMatcher()


def is_condition() -> Matcher[Condition]:
    return ConditionMatcher()
