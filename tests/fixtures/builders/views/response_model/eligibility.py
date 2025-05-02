from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.views.response_model import eligibility


class EligibilityCohortFactory(ModelFactory[eligibility.EligibilityCohort]): ...


class SuitabilityRuleFactory(ModelFactory[eligibility.SuitabilityRule]): ...


class ActionFactory(ModelFactory[eligibility.Action]): ...


class ProcessedSuggestionFactory(ModelFactory[eligibility.ProcessedSuggestion]):
    eligibility_cohorts = Use(EligibilityCohortFactory.batch, size=2)
    suitability_rules = Use(SuitabilityRuleFactory.batch, size=2)
    actions = Use(ActionFactory.batch, size=2)


class EligibilityResponseFactory(ModelFactory[eligibility.EligibilityResponse]):
    processed_suggestions = Use(ProcessedSuggestionFactory.batch, size=2)
