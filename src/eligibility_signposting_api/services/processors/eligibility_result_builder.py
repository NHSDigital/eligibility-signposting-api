from collections import defaultdict

from eligibility_signposting_api.model.eligibility_status import (
    CohortGroupResult,
    Condition,
    ConditionName,
    IterationResult,
)


class EligibilityResultBuilder:
    @staticmethod
    def build_condition_results(condition_results: dict[ConditionName, IterationResult]) -> list[Condition]:
        conditions: list[Condition] = []
        # iterate over conditions
        for condition_name, active_iteration_result in condition_results.items():
            grouped_cohort_results = defaultdict(list)
            # iterate over cohorts and group them by status and cohort_group
            for cohort_result in active_iteration_result.cohort_results:
                if active_iteration_result.status == cohort_result.status:
                    grouped_cohort_results[cohort_result.cohort_code].append(cohort_result)

            # deduplicate grouped cohort results by cohort_code
            deduplicated_cohort_results = [
                CohortGroupResult(
                    cohort_code=group_cohort_code,
                    status=group[0].status,
                    # Flatten all reasons from the group
                    reasons=[reason for cohort in group for reason in cohort.reasons],
                    # get the first nonempty description
                    description=next((c.description for c in group if c.description), group[0].description),
                    audit_rules=[],
                )
                for group_cohort_code, group in grouped_cohort_results.items()
                if group
            ]

            # return condition with cohort results
            conditions.append(
                Condition(
                    condition_name=condition_name,
                    status=active_iteration_result.status,
                    cohort_results=list(deduplicated_cohort_results),
                    actions=condition_results[condition_name].actions,
                    status_text=active_iteration_result.status.get_status_text(condition_name),
                )
            )
        return conditions
