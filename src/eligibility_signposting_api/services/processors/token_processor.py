import re
from dataclasses import Field, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, Never

from wireup import service

from eligibility_signposting_api.config.contants import ALLOWED_CONDITIONS
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.token_parser import ParsedToken, TokenParser

TARGET_ATTRIBUTE_LEVEL = "TARGET"
PERSON_ATTRIBUTE_LEVEL = "PERSON"
ALLOWED_TARGET_ATTRIBUTES = {
    "ATTRIBUTE_TYPE",
    "VALID_DOSES_COUNT",
    "INVALID_DOSES_COUNT",
    "LAST_SUCCESSFUL_DATE",
    "LAST_VALID_DOSE_DATE",
    "BOOKED_APPOINTMENT_DATE",
    "BOOKED_APPOINTMENT_PROVIDER",
    "LAST_INVITE_DATE",
    "LAST_INVITE_STATUS",
}


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
        present_attributes = [attribute.get("ATTRIBUTE_TYPE") for attribute in person.data]

        for token in all_tokens:
            parsed_token = TokenParser.parse(token)
            found_attribute, key_to_replace, replace_with = None, None, None

            attribute_level_map = {
                TARGET_ATTRIBUTE_LEVEL: parsed_token.attribute_value,
                PERSON_ATTRIBUTE_LEVEL: parsed_token.attribute_name,
            }

            key_to_find = attribute_level_map.get(parsed_token.attribute_level)

            if (
                parsed_token.attribute_level == TARGET_ATTRIBUTE_LEVEL
                and parsed_token.attribute_name in ALLOWED_CONDITIONS.__args__
                and parsed_token.attribute_value in ALLOWED_TARGET_ATTRIBUTES
                and parsed_token.attribute_name not in present_attributes
            ):
                replace_with = ""

            if replace_with != "":
                for attribute in person.data:
                    is_person_attribute = attribute.get("ATTRIBUTE_TYPE") == PERSON_ATTRIBUTE_LEVEL
                    is_allowed_target = parsed_token.attribute_name.upper() in ALLOWED_CONDITIONS.__args__
                    is_correct_target = parsed_token.attribute_name.upper() == attribute.get("ATTRIBUTE_TYPE")

                    if ((is_allowed_target and is_correct_target) or is_person_attribute) and key_to_find in attribute:
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
        except Exception as error:
            message = "Invalid value error"
            raise ValueError(message) from error
