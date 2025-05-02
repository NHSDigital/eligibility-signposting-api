from hamcrest.core.matcher import Matcher

from eligibility_signposting_api.model.rules import CampaignConfig, Iteration, IterationRule

from .meta import BaseAutoMatcher


class CampaignConfigMatcher(BaseAutoMatcher[CampaignConfig]): ...


class IterationMatcher(BaseAutoMatcher[Iteration]): ...


class IterationRuleMatcher(BaseAutoMatcher[IterationRule]): ...


def is_campaign_config() -> Matcher[CampaignConfig]:
    return CampaignConfigMatcher()


def is_iteration() -> Matcher[Iteration]:
    return IterationMatcher()


def is_iteration_rule() -> Matcher[IterationRule]:
    return IterationRuleMatcher()
