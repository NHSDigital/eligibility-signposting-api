from datetime import UTC, date, datetime, timedelta
from operator import attrgetter
from random import randint

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from eligibility_signposting_api.model.campaign_config import (
    ActionsMapper,
    AvailableAction,
    CampaignConfig,
    CohortGroup,
    CohortLabel,
    CommsRouting,
    Description,
    Iteration,
    IterationCohort,
    IterationRule,
    RuleAttributeLevel,
    RuleAttributeName,
    RuleComparator,
    RuleDescription,
    RuleName,
    RuleOperator,
    RulePriority,
    RuleType,
    Virtual,
)


def past_date(days_behind: int = 365) -> date:
    return datetime.now(tz=UTC).date() - timedelta(days=randint(1, days_behind))


def future_date(days_ahead: int = 365) -> date:
    return datetime.now(tz=UTC).date() + timedelta(days=randint(1, days_ahead))


class IterationCohortFactory(ModelFactory[IterationCohort]):
    priority = RulePriority(0)
    virtual = Virtual.NO


class IterationRuleFactory(ModelFactory[IterationRule]):
    attribute_target = None
    attribute_name = "DATE_OF_BIRTH"
    operator = "Y>"
    comparator = "-1"
    cohort_label = None
    rule_stop = False


class AvailableActionDetailFactory(ModelFactory[AvailableAction]):
    action_type = "defaultcomms"
    action_code = "action_code"
    action_description = None
    url_link = None
    url_label = None


class ActionsMapperFactory(ModelFactory[ActionsMapper]):
    root = Use(lambda: {"defaultcomms": AvailableActionDetailFactory.build()})


class IterationFactory(ModelFactory[Iteration]):
    iteration_cohorts = Use(IterationCohortFactory.batch, size=2)
    iteration_rules = Use(IterationRuleFactory.batch, size=2)
    iteration_date = Use(past_date)
    default_comms_routing = "defaultcomms"
    actions_mapper = Use(ActionsMapperFactory.build)


class RawCampaignConfigFactory(ModelFactory[CampaignConfig]):
    iterations = Use(IterationFactory.batch, size=2)

    start_date = Use(past_date)
    end_date = Use(future_date)


class CampaignConfigFactory(RawCampaignConfigFactory):
    @classmethod
    def build(cls, **kwargs) -> CampaignConfig:
        """Ensure invariants are met:
        * no iterations with duplicate iteration dates
        * must have iteration active from campaign start date"""
        processed_kwargs = cls.process_kwargs(**kwargs)
        start_date: date = processed_kwargs["start_date"]
        iterations: list[Iteration] = processed_kwargs["iterations"]

        CampaignConfigFactory.fix_iteration_date_invariants(iterations, start_date)

        data = super().build(**processed_kwargs).dict()
        return cls.__model__(**data)

    @staticmethod
    def fix_iteration_date_invariants(iterations: list[Iteration], start_date: date) -> None:
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
    cohort_label = CohortLabel("elid_all_people")
    cohort_group = CohortGroup("magic cohort group")
    positive_description = Description("magic positive description")
    negative_description = Description("magic negative description")
    virtual = Virtual.YES
    priority = 1


class Rsv75RollingCohortFactory(IterationCohortFactory):
    cohort_label = CohortLabel("rsv_75_rolling")
    cohort_group = CohortGroup("rsv_age_range")
    positive_description = Description("rsv_age_range positive description")
    negative_description = Description("rsv_age_range negative description")
    virtual = Virtual.NO
    priority = 2


class Rsv75to79CohortFactory(IterationCohortFactory):
    cohort_label = CohortLabel("rsv_75to79_2024")
    cohort_group = CohortGroup("rsv_age_range")
    positive_description = Description("rsv_age_range positive description")
    negative_description = Description("rsv_age_range negative description")
    virtual = Virtual.NO
    priority = 3


class RsvPretendClinicalCohortFactory(IterationCohortFactory):
    cohort_label = CohortLabel("rsv_pretend_clinical_cohort")
    cohort_group = CohortGroup("rsv_clinical_cohort")
    positive_description = Description("rsv_clinical_cohort positive description")
    negative_description = Description("rsv_clinical_cohort negative description")
    virtual = Virtual.NO
    priority = 4


# Iteration rule factories
class PersonAgeSuppressionRuleFactory(IterationRuleFactory):
    type = RuleType.suppression
    name = RuleName("Exclude too young less than 75")
    description = RuleDescription("Exclude too young less than 75")
    priority = RulePriority(10)
    operator = RuleOperator.year_gt
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("DATE_OF_BIRTH")
    comparator = RuleComparator("-75")


class PostcodeSuppressionRuleFactory(IterationRuleFactory):
    type = RuleType.suppression
    name = RuleName("Excluded postcode In SW19")
    description = RuleDescription("In SW19")
    priority = RulePriority(10)
    operator = RuleOperator.starts_with
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("POSTCODE")
    comparator = RuleComparator("SW19")


class DetainedEstateSuppressionRuleFactory(IterationRuleFactory):
    type = RuleType.suppression
    name = RuleName("Detained - Suppress Individuals In Detained Estates")
    description = RuleDescription("Suppress where individual is identified as being in a Detained Estate")
    priority = RulePriority(160)
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("DE_FLAG")
    operator = RuleOperator.equals
    comparator = RuleComparator("Y")


class ICBFilterRuleFactory(IterationRuleFactory):
    type = RuleType.filter
    name = RuleName("Not in QE1")
    description = RuleDescription("Not in QE1")
    priority = RulePriority(10)
    operator = RuleOperator.ne
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("ICB")
    comparator = RuleComparator("QE1")


class ICBRedirectRuleFactory(IterationRuleFactory):
    type = RuleType.redirect
    name = RuleName("In QE1")
    description = RuleDescription("In QE1")
    priority = RulePriority(20)
    operator = RuleOperator.equals
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("ICB")
    comparator = RuleComparator("QE1")
    comms_routing = CommsRouting("ActionCode1")


class ICBNonEligibleActionRuleFactory(IterationRuleFactory):
    type = RuleType.not_eligible_actions
    name = RuleName("In QE1")
    description = RuleDescription("In QE1")
    priority = RulePriority(20)
    operator = RuleOperator.equals
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("ICB")
    comparator = RuleComparator("QE1")
    comms_routing = CommsRouting("ActionCode1")


class ICBNonActionableActionRuleFactory(IterationRuleFactory):
    type = RuleType.not_actionable_actions
    name = RuleName("In QE1")
    description = RuleDescription("In QE1")
    priority = RulePriority(20)
    operator = RuleOperator.equals
    attribute_level = RuleAttributeLevel.PERSON
    attribute_name = RuleAttributeName("ICB")
    comparator = RuleComparator("QE1")
    comms_routing = CommsRouting("ActionCode1")
