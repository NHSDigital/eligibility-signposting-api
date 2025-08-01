from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelCaseBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RequestAuditHeader(CamelCaseBaseModel):
    x_request_id: str | None = None
    x_correlation_id: str | None = None
    nhsd_end_user_organisation_ods: str | None = None
    nhsd_application_id: str | None = None


class RequestAuditQueryParams(CamelCaseBaseModel):
    category: str | None = None
    conditions: str | None = None
    include_actions: str | None = None


class RequestAuditData(CamelCaseBaseModel):
    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    headers: RequestAuditHeader = Field(default_factory=RequestAuditHeader)
    query_params: RequestAuditQueryParams = Field(default_factory=RequestAuditQueryParams)
    nhs_number: str | None = None


class AuditEligibilityCohorts(CamelCaseBaseModel):
    cohort_code: str | None = None
    cohort_status: str | None = None


class AuditEligibilityCohortGroups(CamelCaseBaseModel):
    cohort_code: str | None = None
    cohort_text: str | None = None
    cohort_status: str | None = None


class AuditFilterRule(CamelCaseBaseModel):
    rule_priority: str | None = None
    rule_name: str | None = None


class AuditSuitabilityRule(CamelCaseBaseModel):
    rule_priority: str | None = None
    rule_name: str | None = None
    rule_message: str | None = None


class AuditRedirectRule(CamelCaseBaseModel):
    rule_priority: str | None = None
    rule_name: str | None = None


class AuditAction(CamelCaseBaseModel):
    internal_action_code: str | None = None
    action_type: str | None = None
    action_code: str | None = None
    action_description: str | None = None
    action_url: str | None = None
    action_url_label: str | None = None


class AuditCondition(CamelCaseBaseModel):
    campaign_id: str | None = None
    campaign_version: int | None = None
    iteration_id: str | None = None
    iteration_version: int | None = None
    condition_name: str | None = None
    status: str | None = None
    status_text: str | None = None
    eligibility_cohorts: list[AuditEligibilityCohorts] | None = None
    eligibility_cohort_groups: list[AuditEligibilityCohortGroups] | None = None
    filter_rules: AuditFilterRule | None = None
    suitability_rules: AuditSuitabilityRule | None = None
    action_rule: AuditRedirectRule | None = None
    actions: list[AuditAction] | None = Field(default_factory=list)


class ResponseAuditData(CamelCaseBaseModel):
    response_id: UUID | None = None
    last_updated: datetime | None = None
    condition: list[AuditCondition] = Field(default_factory=list)


class AuditEvent(CamelCaseBaseModel):
    request: RequestAuditData = Field(default_factory=RequestAuditData)
    response: ResponseAuditData = Field(default_factory=ResponseAuditData)
