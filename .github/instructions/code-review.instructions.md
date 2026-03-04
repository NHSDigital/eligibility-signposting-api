---
description: "Code review instructions for the eligibility-signposting-api project"
applyTo: "**"
excludeAgent: ["coding-agent"]
---

# Code Review Instructions

Guidelines for the eligibility-signposting-api project — a serverless AWS Lambda + Flask eligibility rules engine.

## Review Priorities

### Critical (block merge)

- **Security**: Exposed secrets, PII leakage (especially NHS Numbers), missing header validation
- **Correctness**: Logic errors in rules engine evaluation, incorrect operator behaviour, data corruption in DynamoDB
- **Breaking Changes**: API contract changes to FHIR response models or request validation

### Important (requires discussion)

- **Code Quality**: SOLID violations, excessive duplication
- **Test Coverage**: Missing tests for critical paths, new rules/operators, or edge cases
- **Performance**: Unnecessary DynamoDB scans, missing caching, Lambda cold start regressions
- **Architecture**: Deviations from established patterns (wireup DI, chain of responsibility, operator registry)

### Suggestion (non-blocking)

- **Readability**: Naming, simplification of complex logic
- **Best Practices**: Minor convention deviations
- **Documentation**: Missing or incomplete docstrings

## Security

- **PII handling**: NHS Numbers must never appear in logs or error messages. `TokenError` messages must be redacted. Verify new log statements do not leak person data.
- **Secrets**: No API keys, tokens, or secrets in code. Use environment variables or AWS Secrets Manager.
- **NHS Number hashing**: Lookups use HMAC-SHA512 via `HashingService` with secret rotation (AWSCURRENT → AWSPREVIOUS fallback).
- **Header validation**: `NHSE-Product-ID` must be present (403 if missing). `nhs-login-nhs-number` must match path parameter.
- **Security headers**: Responses must include `Cache-Control: no-store, private`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`.

## Architecture

- **Dependency injection**: Use wireup `@service` for all services, repos, and factories. Inject via `Injected[T]`, `Inject(qualifier=...)`, or `Inject(param=...)`. Never instantiate services manually.
- **Chain of responsibility**: Processing follows `CohortEligibilityHandler → BaseEligibilityHandler → FilterRuleHandler → SuppressionRuleHandler`. Extend this chain for new steps.
- **Operator registry**: New operators must extend `hamcrest.BaseMatcher` and register via the decorator-based `OperatorRegistry`.
- **Pydantic models**: Use `Field(alias=...)` for JSON mapping, `field_validator`/`model_validator` for validation. Response models use camelCase aliases.
- **FHIR compliance**: Error responses must use `OperationOutcome` models with `application/fhir+json` content type.
- **Lambda reuse**: The Flask app is cached in `CacheManager` across invocations. Changes to app initialization must not break container reuse.

## Performance

- **DynamoDB**: Use `query()` with `KeyConditionExpression`, never `scan()`. Partition key is `NHS_NUMBER`, sort key discriminator is `ATTRIBUTE_TYPE`.
- **S3 configuration loading**: Campaign configs load from S3 per request. Avoid unnecessary `list_objects` or `get_object` calls.
- **Caching**: Feature toggles use `TTLCache` (300s). New caching should follow the same pattern with appropriate TTLs.
- **Lambda cold starts**: Avoid heavy imports at module level. Keep wireup service graph lean.

## Audit Trail

- **Completeness**: New eligibility logic must call `AuditContext.append_audit_condition()` to record evaluation details.
- **Firehose delivery**: Audit events use Pydantic `AuditEvent` models sent to Kinesis Firehose. Preserve the full audit data model.

## Terraform

- **Encryption**: All AWS resources (DynamoDB, S3, Lambda, Firehose, Secrets Manager) must use KMS CMK encryption.
- **Environment parity**: Verify deletion protection and PITR are enabled for production/pre-production DynamoDB tables.
- **Safety**: Terraform changes must not destroy or replace stateful resources (DynamoDB tables, S3 buckets) unintentionally.
