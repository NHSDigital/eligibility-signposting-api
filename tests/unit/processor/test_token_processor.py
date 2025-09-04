import pytest

from eligibility_signposting_api.services.processors.token_processor import TokenProcessor, TokenError


@pytest.mark.parametrize(
    ("date_format", "expected"),
    [
        (None, "20250510"),
        ("%Y-%m-%d", "2025-05-10"),
        ("%d/%m/%Y", "10/05/2025"),
        ("%b %d, %Y", "May 10, 2025"),
        ("%A, %d %B %Y", "Saturday, 10 May 2025"),
        ("", ""),
    ],
)
def test_apply_formatting_returns_valid_value(date_format, expected):
    attribute = {"DATE_OF_BIRTH": "20250510"}
    attribute_value = "DATE_OF_BIRTH"

    actual = TokenProcessor.apply_formatting(attribute, attribute_value, date_format)
    assert actual == expected


def test_apply_formatting_attribute_not_present():
    invalid_attribute = {"DATE_OF_BIRTH": "20250510"}
    attribute_value = "ICE_CREAM"
    date_format = None

    actual = TokenProcessor.apply_formatting(invalid_attribute, attribute_value, date_format)

    assert actual == ""


def test_apply_formatting_raises_attribute_error():
    invalid_attribute = "not_a_dict"
    attribute_value = "DATE_OF_BIRTH"
    date_format = None

    with pytest.raises(AttributeError) as exc_info:
        TokenProcessor.apply_formatting(invalid_attribute, attribute_value, date_format)

    assert isinstance(exc_info.value, AttributeError)
    assert str(exc_info.value) == "Invalid token format"


def test_apply_formatting_raises_value_error_on_invalid_date():
    attribute = {"DATE_OF_BIRTH": "invalid"}
    attribute_value = "DATE_OF_BIRTH"
    date_format = "%Y-%m-%d"

    with pytest.raises(TokenError, match="Invalid value error"):
        TokenProcessor.apply_formatting(attribute, attribute_value, date_format)
