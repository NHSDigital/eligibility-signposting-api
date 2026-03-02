import re
from dataclasses import Field, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, Never

from wireup import service

from eligibility_signposting_api.config.constants import ALLOWED_CONDITIONS
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.derived_values import (
    DerivedValueContext,
    get_registry,
)
from eligibility_signposting_api.services.processors.token_parser import ParsedToken, TokenParser

TARGET_ATTRIBUTE_LEVEL = "TARGET"
PERSON_ATTRIBUTE_LEVEL = "PERSON"
ALLOWED_TARGET_ATTRIBUTES = {
    "ATTRIBUTE_TYPE",
    "VALID_DOSES_COUNT",
    "INVALID_DOSES_COUNT",
    "LAST_SUCCESSFUL_DATE",
    "SUCCESSFUL_PROCEDURE_COUNT",
    "LAST_VALID_DOSE_DATE",
    "BOOKED_APPOINTMENT_DATE",
    "BOOKED_APPOINTMENT_PROVIDER",
    "LAST_INVITE_DATE",
    "LAST_INVITE_STATUS",
    "NEXT_DOSE_DUE",
}


class TokenError(Exception):
    """Person value error."""


@service
class TokenProcessor:
    @staticmethod
    def find_and_replace_tokens[T](person: Person, data_class: T) -> T:
        if not is_dataclass(data_class):
            return data_class
        for class_field in fields(data_class):
            value = getattr(data_class, class_field.name)
            if isinstance(value, str):
                setattr(data_class, class_field.name, TokenProcessor.replace_token(value, person))
            elif isinstance(value, list):
                TokenProcessor.process_list(class_field, data_class, person, value)
            elif isinstance(value, dict):
                TokenProcessor.process_dict(class_field, data_class, person, value)
            elif is_dataclass(value):
                setattr(data_class, class_field.name, TokenProcessor.find_and_replace_tokens(person, value))
        return data_class

    @staticmethod
    def process_dict(class_field: Field, data_class: object, person: Person, value: dict[Any, Any]) -> None:
        for key, dict_value in value.items():
            if isinstance(dict_value, str):
                value[key] = TokenProcessor.replace_token(dict_value, person)
            elif is_dataclass(dict_value):
                value[key] = TokenProcessor.find_and_replace_tokens(person, dict_value)
        setattr(data_class, class_field.name, value)

    @staticmethod
    def process_list(class_field: Field, data_class: object, person: Person, value: list[Any]) -> None:
        for i, item in enumerate(value):
            if is_dataclass(item):
                value[i] = TokenProcessor.find_and_replace_tokens(person, item)
            elif isinstance(item, str):
                value[i] = TokenProcessor.replace_token(item, person)
            setattr(data_class, class_field.name, value)

    @staticmethod
    def replace_token(text: str, person: Person) -> str:
        if not isinstance(text, str):
            return text

        pattern = r"\[\[.*?\]\]"
        all_tokens = re.findall(pattern, text, re.IGNORECASE)
        present_attributes = {attribute.get("ATTRIBUTE_TYPE") for attribute in person.data}

        for token in all_tokens:
            replacement = TokenProcessor.get_token_replacement(token, person.data, present_attributes)
            text = text.replace(token, str(replacement))
        return text

    @staticmethod
    def get_token_replacement(token: str, person_data: list[dict], present_attributes: set) -> str:
        parsed_token = TokenParser.parse(token)

        if TokenProcessor.should_replace_with_empty(parsed_token, present_attributes):
            return ""

        if parsed_token.function_name:
            return TokenProcessor.get_derived_value(parsed_token, person_data, present_attributes, token)

        TokenProcessor.validate_target_attribute(parsed_token, token)

        found_attribute, key_to_replace = TokenProcessor.find_matching_attribute(parsed_token, person_data)

        if not found_attribute or not key_to_replace:
            TokenProcessor.handle_token_not_found(parsed_token, token)
            msg = "Unreachable"
            raise RuntimeError(msg)  # pragma: no cover

        return TokenProcessor.apply_formatting(found_attribute, key_to_replace, parsed_token.format)

    @staticmethod
    def get_derived_value(
        parsed_token: ParsedToken,
        person_data: list[dict],
        present_attributes: set,
        token: str,
    ) -> str:
        """Calculate a derived value using the registered handler.

        For TARGET level tokens, validates that the condition is allowed before processing.
        If the vaccine type is not in person data, returns an empty string.
        For derived values, any target attribute name is allowed (e.g., NEXT_BOOKING_AVAILABLE)
        since it's just a placeholder that may be surfaced in the future.

        Args:
            parsed_token: The parsed token containing function information
            person_data: List of person attribute dictionaries
            present_attributes: Set of attribute types present in person data
            token: The original token string for error messages

        Returns:
            The calculated derived value as a string

        Raises:
            ValueError: If no handler is registered or attribute not found
        """
        registry = get_registry()

        function_name = parsed_token.function_name
        if not function_name:
            message = f"No function specified in token '{token}'."
            raise ValueError(message)

        if not registry.has_handler(function_name):
            message = f"Unknown function '{function_name}' in token '{token}'."
            raise ValueError(message)

        if parsed_token.attribute_level == TARGET_ATTRIBUTE_LEVEL:
            is_allowed_condition = parsed_token.attribute_name in ALLOWED_CONDITIONS.__args__

            if not is_allowed_condition:
                TokenProcessor.handle_token_not_found(parsed_token, token)

            if parsed_token.attribute_name not in present_attributes:
                return ""

        try:
            target_attribute = parsed_token.attribute_value or parsed_token.attribute_name
            source_attribute = registry.get_source_attribute(
                function_name,
                target_attribute,
                parsed_token.function_args,
            )

            context = DerivedValueContext(
                person_data=person_data,
                attribute_name=parsed_token.attribute_name,
                source_attribute=source_attribute,
                function_args=parsed_token.function_args,
                date_format=parsed_token.format,
                attribute_level=parsed_token.attribute_level,
            )

            return registry.calculate(
                function_name=function_name,
                context=context,
            )
        except ValueError as e:
            message = f"Error calculating derived value for token '{token}': {e}"
            raise ValueError(message) from e

    @staticmethod
    def should_replace_with_empty(parsed_token: ParsedToken, present_attributes: set) -> bool:
        is_target_level = parsed_token.attribute_level == TARGET_ATTRIBUTE_LEVEL
        is_allowed_condition = parsed_token.attribute_name in ALLOWED_CONDITIONS.__args__
        is_allowed_target_attr = parsed_token.attribute_value in ALLOWED_TARGET_ATTRIBUTES
        is_attr_not_present = parsed_token.attribute_name not in present_attributes

        return all([is_target_level, is_allowed_condition, is_allowed_target_attr, is_attr_not_present])

    @staticmethod
    def validate_target_attribute(parsed_token: ParsedToken, token: str) -> None:
        """Validate that target attribute is allowed for non-derived tokens.

        For regular (non-derived) tokens, only allow known target attributes.
        Derived values with functions can use any custom target attribute name.

        Args:
            parsed_token: The parsed token to validate
            token: The original token string for error messages

        Raises:
            ValueError: If the target attribute is not in ALLOWED_TARGET_ATTRIBUTES
        """
        if (
            parsed_token.attribute_level == TARGET_ATTRIBUTE_LEVEL
            and parsed_token.attribute_value not in ALLOWED_TARGET_ATTRIBUTES
        ):
            TokenProcessor.handle_token_not_found(parsed_token, token)

    @staticmethod
    def find_matching_attribute(parsed_token: ParsedToken, person_data: list[dict]) -> tuple[dict | None, str | None]:
        attribute_level_map = {
            TARGET_ATTRIBUTE_LEVEL: parsed_token.attribute_value,
            PERSON_ATTRIBUTE_LEVEL: parsed_token.attribute_name,
        }
        key_to_find = attribute_level_map.get(parsed_token.attribute_level)

        for attribute in person_data:
            if TokenProcessor.attribute_match(attribute, parsed_token, key_to_find):
                return attribute, key_to_find

        return None, None

    @staticmethod
    def attribute_match(attribute: dict, parsed_token: ParsedToken, key_to_find: str | None) -> bool:
        if not key_to_find or key_to_find not in attribute:
            return False

        is_person_attribute = attribute.get("ATTRIBUTE_TYPE") == PERSON_ATTRIBUTE_LEVEL
        if is_person_attribute:
            return True

        is_allowed_target = parsed_token.attribute_name.upper() in ALLOWED_CONDITIONS.__args__
        is_correct_target = parsed_token.attribute_name.upper() == attribute.get("ATTRIBUTE_TYPE")

        return is_allowed_target and is_correct_target

    @staticmethod
    def handle_token_not_found(parsed_token: ParsedToken, token: str) -> Never:
        if parsed_token.attribute_level == TARGET_ATTRIBUTE_LEVEL:
            message = f"Invalid attribute name '{parsed_token.attribute_value}' in token '{token}'."
            raise ValueError(message)
        if parsed_token.attribute_level == PERSON_ATTRIBUTE_LEVEL:
            message = f"Invalid attribute name '{parsed_token.attribute_name}' in token '{token}'."
            raise ValueError(message)
        message = f"Invalid attribute level '{parsed_token.attribute_level}' in token '{token}'."
        raise ValueError(message)

    @staticmethod
    def apply_formatting[T](attributes: dict[str, T], attribute_name: str, date_format: str | None) -> str:
        try:
            attribute_data = attributes.get(attribute_name)
            if (date_format or date_format == "") and attribute_data:
                replace_with_date_object = datetime.strptime(str(attribute_data), "%Y%m%d").replace(tzinfo=UTC)
                replace_with = replace_with_date_object.strftime(str(date_format))
            else:
                replace_with = attribute_data if attribute_data else ""
            return str(replace_with)
        except AttributeError as error:
            message = "Invalid token format"
            raise AttributeError(message) from error
        except ValueError as error:
            message = "Invalid value error"
            raise TokenError(message) from error
