from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class RequestAuditHeader:
    xRequestID: str
    xCorrelationID: str
    nhsdEndUserOrganisationODS: str
    nhsdApplicationID: str

@dataclass
class RequestAuditQueryParams:
    category: str | None = None
    conditions: str | None = None
    includeActions: str | None = None

@dataclass
class RequestAuditData:
    requestTimestamp: datetime
    headers: RequestAuditHeader
    queryParams: RequestAuditQueryParams
    nhsNumber: int

@dataclass
class AuditEligibilityCohorts:
    cohortCode: str | None = None
    cohortStatus: str | None = None

@dataclass
class AuditEligibilityCohortGroups:
    cohortCode: str | None = None
    cohortText: str | None = None
    cohortStatus: str | None = None

@dataclass
class AuditFilterRule:
    rulePriority: int | None = None
    ruleName: str | None = None

@dataclass
class AuditSuitabilityRule:
    rulePriority: int | None = None
    ruleName: str | None = None
    ruleMessage: str | None = None

@dataclass
class AuditRedirectRule:
    rulePriority: int | None = None
    ruleName: str | None = None

@dataclass
class AuditAction:
    internalName: str | None = None
    actionType: str | None = None
    actionCode: str | None = None
    actionDescription: str | None = None
    actionUrl: str | None = None
    actionUrlLabel: str | None = None

@dataclass
class AuditCondition:
    campaignID: str
    campaignVersion: int
    iterationID: str
    iterationVersion: int
    conditionName: str
    status: str
    statusText: str
    eligibilityCohorts: List[AuditEligibilityCohorts] | None = None
    eligibilityCohortGroups: List[AuditEligibilityCohortGroups] | None = None
    filterRules: AuditFilterRule | None = None
    suitabilityRules: AuditSuitabilityRule | None = None
    actionRule: AuditRedirectRule | None = None
    actions: List[AuditAction] = field(default_factory=list)

@dataclass
class ResponseAuditData:
    responseId: str | None = None
    lastUpdated: str | None = None
    condition: List[AuditCondition] = field(default_factory=list)
