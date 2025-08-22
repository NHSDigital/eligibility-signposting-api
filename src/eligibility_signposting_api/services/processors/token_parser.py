import re
from dataclasses import dataclass


class InvalidTokenError(ValueError):
    def __init__(self, message: str = "Invalid token.") -> None:
        super().__init__(message)


class InvalidTokenFormatError(ValueError):
    def __init__(self, message: str = "Invalid token format.") -> None:
        super().__init__(message)


@dataclass
class ParsedToken:
    attribute_level: str  # example: "PERSON" or "TARGET"
    attribute_name: str  # example: "POSTCODE" or "RSV"
    attribute_value: str | None  # example: "LAST_SUCCESSFUL_DATE" if attribute_level is TARGET
    format: str | None  # example: "%d %B %Y" if DATE formatting is used


class TokenParser:
    MIN_TOKEN_PARTS = 2

    @staticmethod
    def parse(token: str) -> ParsedToken:
        token_body = token[2:-2]  # Strip the surrounding [[ ]]
        # Check for empty body after stripping, e.g., '[[]]'
        if not token_body:
            raise InvalidTokenError

        token_parts = token_body.split(".")

        # Check for empty parts created by leading/trailing dots or tokens with no dot
        if len(token_parts) < TokenParser.MIN_TOKEN_PARTS or not all(token_parts):
            raise InvalidTokenError

        token_level = token_parts[0].upper()
        token_name = token_parts[-1]

        # Check if the name contains a date format
        format_match = re.search(r":DATE\(([^()]*)\)", token_name, re.IGNORECASE)
        if not format_match and len(token_name.split(":")) > 1:
            raise InvalidTokenFormatError

        format_str = format_match.group(1) if format_match else None

        # Remove the date format from the last part
        last_part = re.sub(r":DATE\(.*?\)", "", token_name, flags=re.IGNORECASE)

        if len(token_parts) == TokenParser.MIN_TOKEN_PARTS:
            # Person token, example, [[PERSON.AGE]]
            name = last_part.upper()
            value = None
        else:
            # Target token, example, [[TARGET.RSV.LAST_SUCCESSFUL_DATE]]
            name = token_parts[1].upper()
            value = last_part.upper()

        return ParsedToken(attribute_level=token_level, attribute_name=name, attribute_value=value, format=format_str)
