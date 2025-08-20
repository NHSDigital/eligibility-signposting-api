import pytest

from eligibility_signposting_api.services.calculators.token_parser import TokenParser


class TestTokenParser:
    @pytest.mark.parametrize(
        "token, expected_level, expected_name, expected_value, expected_format",
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
        assert parsed_token.attribute_level == expected_level
        assert parsed_token.attribute_name == expected_name
        assert parsed_token.attribute_value == expected_value
        assert parsed_token.format == expected_format

    def test_parse_malformed_token_raises_error(self):
        with pytest.raises(ValueError):
            TokenParser.parse("[[PERSONAGE]]")
