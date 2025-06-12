from hamcrest.core.matcher import Matcher

from eligibility_signposting_api.model.eligibility import CohortGroupResult, Condition, EligibilityStatus, Reason
from eligibility_signposting_api.views.response_model.eligibility import EligibilityCohort, SuitabilityRule

from .meta import BaseAutoMatcher


class EligibilityStatusMatcher(BaseAutoMatcher[EligibilityStatus]): ...


class ConditionMatcher(BaseAutoMatcher[Condition]): ...


class CohortResultMatcher(BaseAutoMatcher[CohortGroupResult]): ...


class ReasonMatcher(BaseAutoMatcher[Reason]): ...


class EligibilityCohortMatcher(BaseAutoMatcher[EligibilityCohort]): ...


class SuitabilityRuleMatcher(BaseAutoMatcher[SuitabilityRule]): ...


def is_eligibility_status() -> Matcher[EligibilityStatus]:
    return EligibilityStatusMatcher()


def is_condition() -> Matcher[Condition]:
    return ConditionMatcher()


def is_cohort_result() -> Matcher[CohortGroupResult]:
    return CohortResultMatcher()


def is_reason() -> Matcher[Reason]:
    return ReasonMatcher()


def is_eligibility_cohort() -> Matcher[EligibilityCohort]:
    return EligibilityCohortMatcher()


def is_suitability_rule() -> Matcher[SuitabilityRule]:
    return SuitabilityRuleMatcher()
