import pytest
from hamcrest import assert_that, calling, equal_to, is_, raises

from eligibility_signposting_api.services.processors.token_parser import TokenParser


class TestTokenParser:
    @pytest.mark.parametrize(
        ("token", "expected_level", "expected_name", "expected_value", "expected_format"),
        [
            ("[[PERSON.AGE]]", "PERSON", "AGE", None, None),
            ("[[TARGET.RSV.LAST_SUCCESSFUL_DATE]]", "TARGET", "RSV", "LAST_SUCCESSFUL_DATE", None),
            ("[[PERSON.DATE_OF_BIRTH:DATE(%Y-%m-%d)]]", "PERSON", "DATE_OF_BIRTH", None, "%Y-%m-%d"),
            ("[[TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]", "TARGET", "RSV", "LAST_SUCCESSFUL_DATE", "%d %B %Y"),
            ("[[PERSON.DATE_OF_BIRTH:DATE()]]", "PERSON", "DATE_OF_BIRTH", None, ""),
            ("[[person.age]]", "PERSON", "AGE", None, None),
            ("[[PERSON.age]]", "PERSON", "AGE", None, None),
            ("[[TARGET.RSV.last_successful_date]]", "TARGET", "RSV", "LAST_SUCCESSFUL_DATE", None),
            ("[[PERSON.DATE_OF_BIRTH:date(%Y-%m-%d)]]", "PERSON", "DATE_OF_BIRTH", None, "%Y-%m-%d"),
            ("[[PERSON.AGE.EXTRA]]", "PERSON", "AGE", "EXTRA", None),
        ],
    )
    def test_parse_valid_tokens(self, token, expected_level, expected_name, expected_value, expected_format):
        parsed_token = TokenParser.parse(token)
        assert_that(parsed_token.attribute_level, is_(equal_to(expected_level)))
        assert_that(parsed_token.attribute_name, is_(equal_to(expected_name)))
        assert_that(parsed_token.attribute_value, is_(equal_to(expected_value)))
        assert_that(parsed_token.format, is_(equal_to(expected_format)))

    @pytest.mark.parametrize(
        "token",
        [
            "[[.AGE]]",
            "[[PERSON.]]",
            "[[]]",
            "[[PERSON]]",
            "[[.PERSON.AGE]]",
            "[[PERSON.AGE.]]",
        ],
    )
    def test_parse_invalid_tokens_raises_error(self, token):
        assert_that(
            calling(TokenParser.parse).with_args(token),
            raises(ValueError, pattern=r"Invalid token\."),
        )

    @pytest.mark.parametrize(
        "token",
        [
            "[[PERSON.DATE_OF_BIRTH:DATE(]]",
            "[[PERSON.DATE_OF_BIRTH:DATE)]]",
            "[[PERSON.DATE_OF_BIRTH:DATE]]",
            "[[PERSON.DATE_OF_BIRTH:INVALID_FORMAT(a (b) c)]]",
            "[[PERSON.DATE_OF_BIRTH:DATE(a (b) c)]]",
        ],
    )
    def test_parse_invalid_token_format_raises_error(self, token):
        assert_that(
            calling(TokenParser.parse).with_args(token),
            raises(ValueError, pattern=r"Invalid token format\."),
        )

    def test_parse_function_token_valid(self):
        """Test that valid function tokens are parsed correctly."""
        # This used to be invalid, but now we support custom functions
        parsed = TokenParser.parse("[[PERSON.DATE_OF_BIRTH:SOME_FUNC(abc)]]")
        assert_that(parsed.function_name, is_(equal_to("SOME_FUNC")))
        assert_that(parsed.function_args, is_(equal_to("abc")))
