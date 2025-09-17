import re
from dataclasses import dataclass


@dataclass
class ParsedToken:
    """
    A class to represent a parsed token.
    ...
    Attributes
    ----------
    attribute_level : str
        Example: "PERSON" or "TARGET"
    attribute_name : str
        Example: "POSTCODE" or "RSV"
    attribute_value : int
        Example: "LAST_SUCCESSFUL_DATE" if attribute_level is TARGET
    format : str
        Example: "%d %B %Y" if DATE formatting is used
    """

    attribute_level: str
    attribute_name: str
    attribute_value: str | None
    format: str | None


class TokenParser:
    MIN_TOKEN_PARTS = 2

    @staticmethod
    def parse(token: str) -> ParsedToken:
        """Parses a token into its parts.
        Steps:
        Strip the surrounding [[ ]]
        Check for empty body after stripping, e.g., '[[]]'
        Check for empty parts created by leading/trailing dots or tokens with no dot
        Check if the name contains a date format
        Return a ParsedToken object
        """

        token_body = token[2:-2]
        if not token_body:
            message = "Invalid token."
            raise ValueError(message)

        token_parts = token_body.split(".")

        if len(token_parts) < TokenParser.MIN_TOKEN_PARTS or not all(token_parts):
            message = "Invalid token."
            raise ValueError(message)

        token_level = token_parts[0].upper()
        token_name = token_parts[-1]

        format_match = re.search(r":DATE\(([^()]*)\)", token_name, re.IGNORECASE)
        if not format_match and len(token_name.split(":")) > 1:
            message = "Invalid token format."
            raise ValueError(message)

        format_str = format_match.group(1) if format_match else None

        last_part = re.sub(r":DATE\([^)]*\)", "", token_name, flags=re.IGNORECASE)

        if len(token_parts) == TokenParser.MIN_TOKEN_PARTS:
            name = last_part.upper()
            value = None
        else:
            name = token_parts[1].upper()
            value = last_part.upper()

        return ParsedToken(attribute_level=token_level, attribute_name=name, attribute_value=value, format=format_str)
