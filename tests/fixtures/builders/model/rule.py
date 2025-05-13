from datetime import UTC, date, datetime, timedelta
from random import randint

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.model import rules


def past_date(days_behind: int = 365) -> date:
    return datetime.now(tz=UTC).date() - timedelta(days=randint(1, days_behind))


def future_date(days_ahead: int = 365) -> date:
    return datetime.now(tz=UTC).date() + timedelta(days=randint(1, days_ahead))


class IterationCohortFactory(ModelFactory[rules.IterationCohort]): ...


class IterationRuleFactory(ModelFactory[rules.IterationRule]): ...


class IterationFactory(ModelFactory[rules.Iteration]):
    iteration_cohorts = Use(IterationCohortFactory.batch, size=2)
    iteration_rules = Use(IterationRuleFactory.batch, size=2)
    iteration_date = Use(past_date)


class CampaignConfigFactory(ModelFactory[rules.CampaignConfig]):
    iterations = Use(IterationFactory.batch, size=2)

    start_date = Use(past_date)
    end_date = Use(future_date)


class PersonAgeSuppressionRuleFactory(IterationRuleFactory):
    type = rules.RuleType.suppression
    name = rules.RuleName("Exclude too young less than 75")
    description = rules.RuleDescription("Exclude too young less than 75")
    priority = rules.RulePriority(10)
    operator = rules.RuleOperator.year_gt
    attribute_level = rules.RuleAttributeLevel.PERSON
    attribute_name = rules.RuleAttributeName("DATE_OF_BIRTH")
    comparator = rules.RuleComparator("-75")


class PostcodeSuppressionRuleFactory(IterationRuleFactory):
    type = rules.RuleType.suppression
    name = rules.RuleName("In SW19")
    description = rules.RuleDescription("In SW19")
    priority = rules.RulePriority(10)
    operator = rules.RuleOperator.starts_with
    attribute_level = rules.RuleAttributeLevel.PERSON
    attribute_name = rules.RuleAttributeName("POSTCODE")
    comparator = rules.RuleComparator("SW19")
