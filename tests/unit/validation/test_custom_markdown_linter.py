from rules_validation_api.validators.custom_markdown_linter import validate_markdown
import pytest

class TestCustomMarkdownLinter:
    def test_custom_markdown_linter(self):
        valid_markdown = "### This is a valid header\n\nThis is a valid paragraph."

        # Should not raise any exception
        validate_markdown(valid_markdown)

    def test_custom_markdown_linter_invalid(self):
        invalid_markdown = "#InvalidHeader\n*InvalidListItem\nTitle1\n## SubTitle"

        with pytest.raises(ValueError) as exc_info:
            validate_markdown(invalid_markdown)

        error_msg = str(exc_info.value)
        assert "Header missing space after hash" in error_msg
        assert "List item missing space after bullet" in error_msg
        assert "Header must be preceded by a blank line" in error_msg

    def test_custom_markdown_linter_correct_link_format(self):
        valid_link_markdown = "Please visit our [help page](https://www.nhs.uk/nhs-app/)."

        # Should not raise any exception
        validate_markdown(valid_link_markdown)

    def test_custom_markdown_linter_incorrect_link_format(self):
        invalid_link_markdown = "Please visit our [help page] (https://www.nhs.uk/nhs-app/)."

        with pytest.raises(ValueError) as exc_info:
            validate_markdown(invalid_link_markdown)
        assert "Link format invalid: use [text](url) with no spaces" in str(exc_info.value)
