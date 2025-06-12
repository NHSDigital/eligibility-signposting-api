from datetime import UTC, date, datetime, timedelta
from operator import attrgetter
from random import randint

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.model import rules


def past_date(days_behind: int = 365) -> date:
    return datetime.now(tz=UTC).date() - timedelta(days=randint(1, days_behind))


def future_date(days_ahead: int = 365) -> date:
    return datetime.now(tz=UTC).date() + timedelta(days=randint(1, days_ahead))


class IterationCohortFactory(ModelFactory[rules.IterationCohort]):
    priority = rules.RulePriority(0)


class IterationRuleFactory(ModelFactory[rules.IterationRule]):
    attribute_target = None
    attribute_name = None
    cohort_label = None
    rule_stop = False


class IterationFactory(ModelFactory[rules.Iteration]):
    iteration_cohorts = Use(IterationCohortFactory.batch, size=2)
    iteration_rules = Use(IterationRuleFactory.batch, size=2)
    iteration_date = Use(past_date)


class RawCampaignConfigFactory(ModelFactory[rules.CampaignConfig]):
    iterations = Use(IterationFactory.batch, size=2)

    start_date = Use(past_date)
    end_date = Use(future_date)


class CampaignConfigFactory(RawCampaignConfigFactory):
    @classmethod
    def build(cls, **kwargs) -> rules.CampaignConfig:
        """Ensure invariants are met:
        * no iterations with duplicate iteration dates
        * must have iteration active from campaign start date"""
        processed_kwargs = cls.process_kwargs(**kwargs)
        start_date: date = processed_kwargs["start_date"]
        iterations: list[rules.Iteration] = processed_kwargs["iterations"]

        CampaignConfigFactory.fix_iteration_date_invariants(iterations, start_date)

        data = super().build(**processed_kwargs).dict()
        return cls.__model__(**data)

    @staticmethod
    def fix_iteration_date_invariants(iterations: list[rules.Iteration], start_date: date) -> None:
        iterations.sort(key=attrgetter("iteration_date"))
        iterations[0].iteration_date = start_date

        seen: set[date] = set()
        previous: date = iterations[0].iteration_date
        for iteration in iterations:
            current = iteration.iteration_date if iteration.iteration_date >= previous else previous + timedelta(days=1)
            while current in seen:
                current += timedelta(days=1)
            seen.add(current)
            iteration.iteration_date = current
            previous = current


# Iteration cohort factories
class MagicCohortFactory(IterationCohortFactory):
    cohort_label = rules.CohortLabel("elid_all_people")
    cohort_group = rules.CohortGroup("magic cohort group")
    positive_description = rules.Description("magic positive description")
    negative_description = rules.Description("magic negative description")
    priority = 1


class Rsv75RollingCohortFactory(IterationCohortFactory):
    cohort_label = rules.CohortLabel("rsv_75_rolling")
    cohort_group = rules.CohortGroup("rsv_age_range")
    positive_description = rules.Description("rsv_age_range positive description")
    negative_description = rules.Description("rsv_age_range negative description")
    priority = 2


class Rsv75to79CohortFactory(IterationCohortFactory):
    cohort_label = rules.CohortLabel("rsv_75to79_2024")
    cohort_group = rules.CohortGroup("rsv_age_range")
    positive_description = rules.Description("rsv_age_range positive description")
    negative_description = rules.Description("rsv_age_range negative description")
    priority = 3


class RsvPretendClinicalCohortFactory(IterationCohortFactory):
    cohort_label = rules.CohortLabel("rsv_pretend_clinical_cohort")
    cohort_group = rules.CohortGroup("rsv_clinical_cohort")
    positive_description = rules.Description("rsv_clinical_cohort positive description")
    negative_description = rules.Description("rsv_clinical_cohort negative description")
    priority = 4


# Iteration rule factories
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
    name = rules.RuleName("Excluded postcode In SW19")
    description = rules.RuleDescription("In SW19")
    priority = rules.RulePriority(10)
    operator = rules.RuleOperator.starts_with
    attribute_level = rules.RuleAttributeLevel.PERSON
    attribute_name = rules.RuleAttributeName("POSTCODE")
    comparator = rules.RuleComparator("SW19")


class DetainedEstateSuppressionRuleFactory(IterationRuleFactory):
    type = rules.RuleType.suppression
    name = rules.RuleName("Detained - Suppress Individuals In Detained Estates")
    description = rules.RuleDescription("Suppress where individual is identified as being in a Detained Estate")
    priority = rules.RulePriority(160)
    attribute_level = rules.RuleAttributeLevel.PERSON
    attribute_name = rules.RuleAttributeName("DE_FLAG")
    operator = rules.RuleOperator.equals
    comparator = rules.RuleComparator("Y")


class ICBFilterRuleFactory(IterationRuleFactory):
    type = rules.RuleType.filter
    name = rules.RuleName("Not in QE1")
    description = rules.RuleDescription("Not in QE1")
    priority = rules.RulePriority(10)
    operator = rules.RuleOperator.ne
    attribute_level = rules.RuleAttributeLevel.PERSON
    attribute_name = rules.RuleAttributeName("ICB")
    comparator = rules.RuleComparator("QE1")
