from hamcrest.core.matcher import Matcher

from eligibility_signposting_api.model.eligibility import CohortResult, Condition, EligibilityStatus, Reason
from eligibility_signposting_api.model.rules import IterationCohort

from .meta import BaseAutoMatcher


class EligibilityStatusMatcher(BaseAutoMatcher[EligibilityStatus]): ...


class ConditionMatcher(BaseAutoMatcher[Condition]): ...


class CohortResultMatcher(BaseAutoMatcher[CohortResult]): ...


class ReasonMatcher(BaseAutoMatcher[Reason]): ...


class IterationCohortMatcher(BaseAutoMatcher[IterationCohort]): ...


def is_eligibility_status() -> Matcher[EligibilityStatus]:
    return EligibilityStatusMatcher()


def is_condition() -> Matcher[Condition]:
    return ConditionMatcher()


def is_cohort_result() -> Matcher[CohortResult]:
    return CohortResultMatcher()


def is_reason() -> Matcher[Reason]:
    return ReasonMatcher()


def is_iteration_cohort() -> Matcher[IterationCohort]:
    return IterationCohortMatcher()
