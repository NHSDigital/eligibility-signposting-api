"""Tests for TokenParser with derived value function support."""

from dataclasses import dataclass

import pytest

from eligibility_signposting_api.services.processors.token_parser import TokenParser


@dataclass
class ExpectedTokenResult:
    """Expected result for a parsed token."""

    level: str
    name: str
    value: str | None
    function: str | None
    args: str | None
    date_format: str | None


class TestTokenParserWithFunctions:
    """Tests for parsing tokens with function calls like ADD_DAYS."""

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            # Basic ADD_DAYS function
            (
                "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]",
                ExpectedTokenResult("TARGET", "COVID", "NEXT_DOSE_DUE", "ADD_DAYS", "91", None),
            ),
            # ADD_DAYS with date format
            (
                "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]]",
                ExpectedTokenResult("TARGET", "COVID", "NEXT_DOSE_DUE", "ADD_DAYS", "91", "%d %B %Y"),
            ),
            # Different vaccine type
            (
                "[[TARGET.RSV.NEXT_DOSE_DUE:ADD_DAYS(365)]]",
                ExpectedTokenResult("TARGET", "RSV", "NEXT_DOSE_DUE", "ADD_DAYS", "365", None),
            ),
            # Case insensitive function name
            (
                "[[TARGET.COVID.NEXT_DOSE_DUE:add_days(91)]]",
                ExpectedTokenResult("TARGET", "COVID", "NEXT_DOSE_DUE", "ADD_DAYS", "91", None),
            ),
            # Empty args (use default)
            (
                "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS()]]",
                ExpectedTokenResult("TARGET", "COVID", "NEXT_DOSE_DUE", "ADD_DAYS", "", None),
            ),
            # Person level with function (hypothetical future use)
            (
                "[[PERSON.SOME_DATE:ADD_DAYS(30)]]",
                ExpectedTokenResult("PERSON", "SOME_DATE", None, "ADD_DAYS", "30", None),
            ),
        ],
    )
    def test_parse_tokens_with_functions(self, token: str, expected: ExpectedTokenResult):
        """Test parsing tokens with function calls."""
        parsed_token = TokenParser.parse(token)

        assert parsed_token.attribute_level == expected.level
        assert parsed_token.attribute_name == expected.name
        assert parsed_token.attribute_value == expected.value
        assert parsed_token.function_name == expected.function
        assert parsed_token.function_args == expected.args
        assert parsed_token.format == expected.date_format

    def test_parse_without_function_has_none_function_fields(self):
        """Test that tokens without functions have None for function fields."""
        parsed = TokenParser.parse("[[TARGET.COVID.LAST_SUCCESSFUL_DATE]]")

        assert parsed.function_name is None
        assert parsed.function_args is None

    def test_parse_date_format_not_treated_as_function(self):
        """Test that DATE format is not treated as a derived function."""
        parsed = TokenParser.parse("[[PERSON.DATE_OF_BIRTH:DATE(%d %B %Y)]]")

        assert parsed.function_name is None
        assert parsed.format == "%d %B %Y"

    @pytest.mark.parametrize(
        "token",
        [
            "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS]]",  # Missing parentheses
            "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(]]",  # Unclosed parenthesis
            "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS)]]",  # No opening parenthesis
        ],
    )
    def test_parse_invalid_function_format_raises_error(self, token):
        """Test that malformed function calls raise errors."""
        with pytest.raises(ValueError, match="Invalid token format"):
            TokenParser.parse(token)
