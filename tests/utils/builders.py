import random
import string

from polyfactory import Use
from polyfactory.factories import DataclassFactory
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.model.eligibility import Condition, EligibilityStatus
from eligibility_signposting_api.model.rules import CampaignConfig, Iteration, IterationCohort, IterationRule
from eligibility_signposting_api.views.response_models import (
    Action,
    EligibilityCohort,
    EligibilityResponse,
    ProcessedSuggestion,
    SuitabilityRule,
)


class IterationCohortFactory(ModelFactory[IterationCohort]): ...


class IterationRuleFactory(ModelFactory[IterationRule]): ...


class IterationFactory(ModelFactory[Iteration]):
    iteration_cohorts = Use(IterationCohortFactory.batch, size=2)
    iteration_rules = Use(IterationRuleFactory.batch, size=2)


class CampaignConfigFactory(ModelFactory[CampaignConfig]):
    iterations = Use(IterationFactory.batch, size=2)


class EligibilityCohortFactory(ModelFactory[EligibilityCohort]): ...


class SuitabilityRuleFactory(ModelFactory[SuitabilityRule]): ...


class ActionFactory(ModelFactory[Action]): ...


class ProcessedSuggestionFactory(ModelFactory[ProcessedSuggestion]):
    eligibility_cohorts = Use(EligibilityCohortFactory.batch, size=2)
    suitability_rules = Use(SuitabilityRuleFactory.batch, size=2)
    actions = Use(ActionFactory.batch, size=2)


class EligibilityResponseFactory(ModelFactory[EligibilityResponse]):
    processed_suggestions = Use(ProcessedSuggestionFactory.batch, size=2)


class ConditionFactory(DataclassFactory[Condition]): ...


class EligibilityStatusFactory(DataclassFactory[EligibilityStatus]):
    condition = Use(ConditionFactory.batch, size=2)


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))  # noqa: S311
