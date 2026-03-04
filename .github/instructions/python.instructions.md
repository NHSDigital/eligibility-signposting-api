---
description: "Python coding standards for the eligibility-signposting-api project"
applyTo: "**/*.py"
---

# Python Coding Standards

## Naming Conventions

- `snake_case` for functions, variables, and module names.
- `PascalCase` for class names.
- `UPPER_SNAKE_CASE` for constants.
- Prefix private methods and attributes with `_`.

## Code Style

- Line length limit: 120 characters (enforced by ruff).
- Use type hints for all function signatures and return types.
- Prefer `dataclass` for simple domain objects, Pydantic `BaseModel` for validated/serialized models.
- Use `StrEnum` for string enumerations.
- Avoid bare `except:` — catch specific exceptions.

## Error Handling

```python
# Bad: silent failure
try:
    person = repo.get(nhs_number)
except Exception:
    pass

# Good: specific exceptions with context
try:
    person = repo.get(nhs_number)
except PersonNotFoundError:
    raise
except ClientError as e:
    raise RepositoryError(f"Failed to query person table: {e}") from e
```

## Dependency Injection (wireup)

- Decorate services with `@service`. Do not instantiate services manually.
- Use `Inject(qualifier=...)` for AWS client disambiguation.
- Use `Inject(param=...)` for configuration values.
- Register factory functions with `@service` for boto3 clients.

```python
# Good
@service
class MyService:
    def __init__(self, repo: Injected[MyRepo]) -> None:
        self._repo = repo

# Bad: manual instantiation
class MyService:
    def __init__(self) -> None:
        self._repo = MyRepo()
```

## Pydantic Models

- Use `Field(alias=...)` for JSON key mapping.
- Use `field_validator` / `model_validator` for custom validation.
- Response models must use camelCase aliases (`alias_generator=to_camel` or explicit aliases).
- Use `model_dump(by_alias=True)` when serializing for API responses.

## Testing

- Use `pytest` with pyHamcrest assertions (`assert_that`, `is_`, `has_entries`, `contains_exactly`, etc.).
- Use `brunns-matchers` for Werkzeug response assertions.
- Use project auto-matchers (`BaseAutoMatcher`) for dataclass/Pydantic model assertions.
- Use `polyfactory` (`DataclassFactory` / `ModelFactory`) for test data builders.
- Mock AWS services with `moto`, not manual stubs.
- Use `@pytest.mark.parametrize` for rule/operator test cases.

```python
# Good: pyHamcrest with specific matchers
def test_eligible_person_returns_eligible_status():
    result = evaluate(person, campaign)
    assert_that(result, is_(has_property("status", equal_to(Status.ELIGIBLE))))

# Bad: generic assert
def test_eligible():
    result = evaluate(person, campaign)
    assert result is not None
```

## Logging

- Use structured JSON logging via `python-json-logger`.
- Never log NHS Numbers or other PII.
- Include `request_id` via the `ContextVar` pattern for request tracing.
