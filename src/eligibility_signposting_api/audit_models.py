from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RequestAuditHeader:
    x_request_id: str = None
    x_correlation_id: str = None
    nhsd_end_user_organisation_ods: str = None
    nhsd_application_id: str = None


@dataclass
class RequestAuditQueryParams:
    category: str | None = None
    conditions: str | None = None
    include_actions: str | None = None


@dataclass
class RequestAuditData:
    request_timestamp: datetime = field(default_factory=datetime.utcnow)
    headers: RequestAuditHeader = field(default_factory=RequestAuditHeader)
    query_params: RequestAuditQueryParams = field(default_factory=RequestAuditQueryParams)
    nhs_number: str | None = None


@dataclass
class AuditEligibilityCohorts:
    cohort_code: str | None = None
    cohort_status: str | None = None


@dataclass
class AuditEligibilityCohortGroups:
    cohort_code: str | None = None
    cohort_text: str | None = None
    cohort_status: str | None = None


@dataclass
class AuditFilterRule:
    rule_priority: int | None = None
    rule_name: str | None = None


@dataclass
class AuditSuitabilityRule:
    rule_priority: int | None = None
    rule_name: str | None = None
    rule_message: str | None = None


@dataclass
class AuditRedirectRule:
    rule_priority: int | None = None
    rule_name: str | None = None


@dataclass
class AuditAction:
    internal_name: str | None = None
    action_type: str | None = None
    action_code: str | None = None
    action_description: str | None = None
    action_url: str | None = None
    action_url_label: str | None = None


@dataclass
class AuditCondition:
    campaign_id: str = None
    campaign_version: str = None
    iteration_id: str = None
    iteration_version: str = None
    condition_name: str = None
    status: str = None
    status_text: str = None
    eligibility_cohorts: list[AuditEligibilityCohorts] | None = None
    eligibility_cohort_groups: list[AuditEligibilityCohortGroups] | None = None
    filter_rules: AuditFilterRule | None = None
    suitability_rules: AuditSuitabilityRule | None = None
    action_rule: AuditRedirectRule | None = None
    actions: list[AuditAction] = field(default_factory=list)


@dataclass
class ResponseAuditData:
    response_id: str | None = None
    last_updated: str | None = None
    condition: list[AuditCondition] = field(default_factory=list)


@dataclass
class AuditEvent:
    request: RequestAuditData = field(default_factory=RequestAuditData)
    response: ResponseAuditData = field(default_factory=ResponseAuditData)
