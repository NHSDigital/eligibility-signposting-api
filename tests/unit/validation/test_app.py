import sys
from io import StringIO
from unittest.mock import Mock, PropertyMock

from pydantic import BaseModel, ValidationError

from rules_validation_api.app import display_current_iteration, refine_error


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


def test_no_current_iteration():
    # Arrange
    result = Mock()
    type(result.campaign_config).current_iteration = PropertyMock(side_effect=StopIteration)

    captured = StringIO()
    sys.stdout = captured

    # Act
    display_current_iteration(result)

    # Reset stdout
    sys.stdout = sys.__stdout__

    # Assert
    assert "There is no Current Iteration" in captured.getvalue()


def test_current_iteration_exists():
    # Arrange
    mock_iteration = Mock()
    mock_iteration.iteration_number = 7

    result = Mock()
    type(result.campaign_config).current_iteration = PropertyMock(return_value=mock_iteration)

    captured = StringIO()
    sys.stdout = captured

    # Act
    display_current_iteration(result)

    # Reset stdout
    sys.stdout = sys.__stdout__

    # Assert
    assert "Current Iteration Number is" in captured.getvalue()
    assert "7" in captured.getvalue()
