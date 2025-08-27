import re
from dataclasses import Field, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, Never, TypeVar

from wireup import service

from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.token_parser import ParsedToken, TokenParser

T = TypeVar("T")


@service
class TokenProcessor:
    @staticmethod
    def find_and_replace_tokens(person: Person, data_class: T) -> T:
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
        allowed_target_attributes = [
            "NHS_NUMBER",
            "ATTRIBUTE_TYPE",
            "VALID_DOSES_COUNT",
            "INVALID_DOSES_COUNT",
            "LAST_SUCCESSFUL_DATE",
            "LAST_VALID_DOSE_DATE",
            "BOOKED_APPOINTMENT_DATE",
            "BOOKED_APPOINTMENT_PROVIDER",
            "LAST_INVITE_DATE",
            "LAST_INVITE_STATUS",
        ]

        for token in all_tokens:
            parsed_token = TokenParser.parse(token)
            found_attribute, key_to_replace = None, None

            attribute_level_map = {
                "TARGET": parsed_token.attribute_value,
                "PERSON": parsed_token.attribute_name,
            }

            key_to_find = attribute_level_map.get(parsed_token.attribute_level)

            for attribute in person.data:
                is_target_attribute = attribute.get("ATTRIBUTE_TYPE") == parsed_token.attribute_name.upper()
                is_person_attribute = attribute.get("ATTRIBUTE_TYPE") == "PERSON"
                is_target_rsv = parsed_token.attribute_name.upper() == "RSV"

                valid_person_attribute = is_person_attribute and key_to_find in attribute
                valid_target_attribute = (
                    is_target_attribute and is_target_rsv and key_to_find in allowed_target_attributes
                )

                if valid_target_attribute or valid_person_attribute:
                    found_attribute = attribute
                    key_to_replace = key_to_find
                    break

            if not found_attribute or key_to_replace is None:
                TokenProcessor.handle_token_not_found(parsed_token, token)

            replace_with = TokenProcessor.apply_formatting(found_attribute, key_to_replace, parsed_token.format)
            text = text.replace(token, str(replace_with))

        return text

    @staticmethod
    def handle_token_not_found(parsed_token: ParsedToken, token: str) -> Never:
        if parsed_token.attribute_level == "TARGET":
            message = f"Invalid attribute name '{parsed_token.attribute_value}' in token '{token}'."
            raise ValueError(message)
        if parsed_token.attribute_level == "PERSON":
            message = f"Invalid attribute name '{parsed_token.attribute_name}' in token '{token}'."
            raise ValueError(message)
        message = f"Invalid attribute level '{parsed_token.attribute_level}' in token '{token}'."
        raise ValueError(message)

    @staticmethod
    def apply_formatting(attribute: dict[str, T], attribute_value: str, date_format: str | None) -> str:
        try:
            attribute_data = attribute.get(attribute_value)
            if (date_format or date_format == "") and attribute_data:
                replace_with_date_object = datetime.strptime(str(attribute_data), "%Y%m%d").replace(tzinfo=UTC)
                replace_with = replace_with_date_object.strftime(str(date_format))
            else:
                replace_with = attribute_data if attribute_data else ""
            return str(replace_with)
        except AttributeError as error:
            message = "Invalid token format"
            raise AttributeError(message) from error
