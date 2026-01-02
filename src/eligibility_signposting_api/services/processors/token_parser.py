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
    attribute_value : str | None
        Example: "LAST_SUCCESSFUL_DATE" if attribute_level is TARGET
    format : str | None
        Example: "%d %B %Y" if DATE formatting is used
    function_name : str | None
        Example: "ADD_DAYS" for derived value functions
    function_args : str | None
        Example: "91" for ADD_DAYS(91)
    """

    attribute_level: str
    attribute_name: str
    attribute_value: str | None
    format: str | None
    function_name: str | None = None
    function_args: str | None = None


class TokenParser:
    MIN_TOKEN_PARTS = 2
    # Pattern for function calls like ADD_DAYS(91) - captures function name and args
    FUNCTION_PATTERN = re.compile(r":([A-Z_]+)\(([^()]*)\)", re.IGNORECASE)
    # Pattern for DATE format - special case as it's already supported
    DATE_PATTERN = re.compile(r":DATE\(([^()]*)\)", re.IGNORECASE)

    @staticmethod
    def parse(token: str) -> ParsedToken:
        """Parses a token into its parts.
        Steps:
        Strip the surrounding [[ ]]
        Check for empty body after stripping, e.g., '[[]]'
        Check for empty parts created by leading/trailing dots or tokens with no dot
        Check if the name contains a date format or function call
        Return a ParsedToken object

        Supported formats:
        - [[PERSON.AGE]] - Simple person attribute
        - [[TARGET.COVID.LAST_SUCCESSFUL_DATE]] - Target attribute
        - [[PERSON.DATE_OF_BIRTH:DATE(%d %B %Y)]] - With date formatting
        - [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]] - Derived value function
        - [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]] - Function with date format
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

        # Extract function call (e.g., ADD_DAYS(91))
        function_name, function_args = TokenParser._extract_function(token_name)

        # Extract date format
        format_match = TokenParser.DATE_PATTERN.search(token_name)
        format_str = format_match.group(1) if format_match else None

        # Validate format - if there's a colon but no valid pattern, it's invalid
        if not format_match and not function_name and len(token_name.split(":")) > 1:
            message = "Invalid token format."
            raise ValueError(message)

        # Remove function and date patterns to get the clean attribute name
        last_part = TokenParser._clean_attribute_name(token_name)

        if len(token_parts) == TokenParser.MIN_TOKEN_PARTS:
            name = last_part.upper()
            value = None
        else:
            name = token_parts[1].upper()
            value = last_part.upper()

        return ParsedToken(
            attribute_level=token_level,
            attribute_name=name,
            attribute_value=value,
            format=format_str,
            function_name=function_name,
            function_args=function_args,
        )

    @staticmethod
    def _extract_function(token_name: str) -> tuple[str | None, str | None]:
        """Extract function name and arguments from token name.

        Args:
            token_name: The last part of the token (e.g., 'NEXT_DOSE_DUE:ADD_DAYS(91)')

        Returns:
            Tuple of (function_name, function_args) or (None, None) if no function
        """
        # Find all function matches (excluding DATE which is handled separately)
        for match in TokenParser.FUNCTION_PATTERN.finditer(token_name):
            func_name = match.group(1).upper()
            if func_name != "DATE":
                return func_name, match.group(2)
        return None, None

    @staticmethod
    def _clean_attribute_name(token_name: str) -> str:
        """Remove function calls and date formatting from token name.

        Args:
            token_name: The raw token name with potential modifiers

        Returns:
            Clean attribute name
        """
        # Remove date format and other function calls
        without_date = TokenParser.DATE_PATTERN.sub("", token_name)
        return TokenParser.FUNCTION_PATTERN.sub("", without_date)
