import sys
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import Mock, PropertyMock, patch

from pydantic import BaseModel, ValidationError

from rules_validation_api.app import display_current_iteration, refine_error
from tests.unit.validation.conftest import UK_TIMEZONE


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
    result.campaign_config = Mock()

    # iterations must be a list, not a Mock
    result.campaign_config.iterations = []

    result.campaign_config.end_date = datetime.now(UK_TIMEZONE).date() + timedelta(days=1)

    # current_iteration should raise StopIteration
    type(result.campaign_config).current_iteration = PropertyMock(side_effect=StopIteration)

    captured = StringIO()
    sys.stdout = captured

    # Act
    display_current_iteration(result)

    # Reset stdout
    sys.stdout = sys.__stdout__

    # Assert
    assert "No active iteration could be determined" in captured.getvalue()


def test_current_iteration_exists():
    # Arrange
    mock_iteration = Mock()
    mock_iteration.iteration_number = 7
    mock_iteration.iteration_date = datetime.now(UK_TIMEZONE).date() - timedelta(days=1)

    result = Mock()
    result.campaign_config = Mock()

    result.campaign_config.iterations = [mock_iteration]
    result.campaign_config.end_date = datetime.now(UK_TIMEZONE).date() + timedelta(days=1)

    type(result.campaign_config).current_iteration = PropertyMock(return_value=mock_iteration)

    captured = StringIO()
    sys.stdout = captured

    display_current_iteration(result)

    sys.stdout = sys.__stdout__

    assert "Current active Iteration Number:" in captured.getvalue()
    assert "7" in captured.getvalue()


def test_next_iteration_exists():
    # Given
    today = datetime.now(UK_TIMEZONE).date()

    # Setup
    next_mock = Mock()
    next_mock.iteration_number = 8
    next_mock.iteration_date = today + timedelta(days=5)
    next_mock.iteration_datetime = datetime.combine(
        next_mock.iteration_date,
        datetime.min.time(),
        tzinfo=UK_TIMEZONE,
    )

    result = Mock()
    result.campaign_config.end_date = today + timedelta(days=10)
    result.campaign_config.iterations = [next_mock]
    result.campaign_config.campaign_live = False  # To focus only on Next Iteration output

    captured = StringIO()
    sys.stdout = captured

    # When
    display_current_iteration(result)
    sys.stdout = sys.__stdout__
    output = captured.getvalue()

    # Then
    assert "Next active Iteration Number:" in output
    assert "8" in output
    assert str(today + timedelta(days=5)) in output


def test_campaign_expired_and_no_next_iteration():
    """Covers: is_campaign_expired = True, next iteration logic skipped."""
    today = datetime.now(UK_TIMEZONE).date()

    result = Mock()
    config = result.campaign_config
    config.campaign_live = False
    config.end_date = today - timedelta(days=1)  # Expired
    config.iterations = []

    captured = StringIO()
    with patch("sys.stdout", new=captured):
        display_current_iteration(result)

    output = captured.getvalue()
    assert "NOT LIVE" in output
    assert "EXPIRED on" in output
    assert "Next active Iteration Number" not in output


def test_campaign_to_be_started():
    """Covers: is_campaign_expired = False, campaign_live = False."""
    today = datetime.now(UK_TIMEZONE).date()

    result = Mock()
    config = result.campaign_config
    config.campaign_live = False
    config.end_date = today + timedelta(days=10)
    config.start_date = today + timedelta(days=2)
    config.iterations = []

    captured = StringIO()
    with patch("sys.stdout", new=captured):
        display_current_iteration(result)

    output = captured.getvalue()
    assert "NOT LIVE" in output
    assert "To be STARTED on" in output


def test_next_iteration_stop_iteration_exception():
    """
    Covers the 'except StopIteration' block in the Next Iteration section.
    This triggers if the generator inside next() raises StopIteration explicitly.
    """
    today = datetime.now(UK_TIMEZONE).date()

    result = Mock()
    config = result.campaign_config
    config.campaign_live = False
    config.end_date = today + timedelta(days=10)
    config.iterations = [Mock(iteration_date=today + timedelta(days=5))]

    captured = StringIO()
    with patch("sys.stdout", new=captured), patch("rules_validation_api.app.next", side_effect=StopIteration):
        display_current_iteration(result)

    output = captured.getvalue()
    assert "No next active iteration could be determined" in output


def test_next_iteration_is_none():
    today = datetime.now(UK_TIMEZONE).date()

    result = Mock()
    config = result.campaign_config
    config.campaign_live = False
    config.end_date = today + timedelta(days=10)

    past_iteration = Mock()
    past_iteration.iteration_date = today - timedelta(days=5)
    config.iterations = [past_iteration]

    captured = StringIO()
    with patch("sys.stdout", new=captured):
        display_current_iteration(result)

    output = captured.getvalue()

    assert "Next active Iteration Number" not in output
    assert "Total iterations configured:" in output
    assert "1" in output
