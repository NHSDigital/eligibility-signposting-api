from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.views.response_model import eligibility_response


class EligibilityCohortFactory(ModelFactory[eligibility_response.EligibilityCohort]): ...


class SuitabilityRuleFactory(ModelFactory[eligibility_response.SuitabilityRule]): ...


class ActionFactory(ModelFactory[eligibility_response.Action]): ...


class ProcessedSuggestionFactory(ModelFactory[eligibility_response.ProcessedSuggestion]):
    eligibility_cohorts = Use(EligibilityCohortFactory.batch, size=2)
    suitability_rules = Use(SuitabilityRuleFactory.batch, size=2)
    actions = Use(ActionFactory.batch, size=2)


class EligibilityResponseFactory(ModelFactory[eligibility_response.EligibilityResponse]):
    processed_suggestions = Use(ProcessedSuggestionFactory.batch, size=2)
