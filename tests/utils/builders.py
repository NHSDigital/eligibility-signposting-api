import random
import string

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.model.rules import CampaignConfig, Iteration, IterationCohort, IterationRule


class IterationCohortFactory(ModelFactory[IterationCohort]): ...


class IterationRuleFactory(ModelFactory[IterationRule]): ...


class IterationFactory(ModelFactory[Iteration]):
    iteration_cohorts = Use(IterationCohortFactory.batch, size=2)
    iteration_rules = Use(IterationRuleFactory.batch, size=2)


class CampaignConfigFactory(ModelFactory[CampaignConfig]):
    iterations = Use(IterationFactory.batch, size=2)


def random_str(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))  # noqa: S311
