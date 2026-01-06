from pydantic import BaseModel, ValidationError

from rules_validation_api.app import refine_error


def _raise_validation_error(model_cls, **kwargs) -> ValidationError:
    try:
        model_cls(**kwargs)
    except ValidationError as e:
        return e
    msg = "ValidationError was not raised"
    raise AssertionError(msg)


def test_refine_error_single_error():
    class Model(BaseModel):
        x: int

    error = _raise_validation_error(Model, x="not-an-int")

    result = refine_error(error)

    assert "Validation Error: 1 validation error(s)" in result
    assert "x" in result
    assert "type=" in result


def test_refine_error_multiple_errors():
    class Model(BaseModel):
        a: int
        b: int

    error = _raise_validation_error(Model, a="bad", b="also-bad")

    result = refine_error(error)

    assert "Validation Error: 2 validation error(s)" in result
    assert "a" in result
    assert "b" in result
    expected_error_count = 2
    assert result.count("type=") == expected_error_count


def test_refine_error_nested_location():
    class Inner(BaseModel):
        value: int

    class Outer(BaseModel):
        inner: Inner

    error = _raise_validation_error(Outer, inner={"value": "bad"})

    result = refine_error(error)

    assert "inner.value" in result
    assert "type=" in result


def test_refine_error_output_structure():
    class Model(BaseModel):
        x: int
        y: int

    error = _raise_validation_error(Model, x="bad", y="bad")

    result = refine_error(error)

    lines = result.splitlines()

    expected_no_lines = 3
    assert len(lines) == expected_no_lines
    assert lines[0].startswith("❌Validation Error:")
