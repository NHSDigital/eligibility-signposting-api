import re
from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import TypeVar

from wireup import service

from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.token_parser import TokenParser

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
                for i, item in enumerate(value):
                    if is_dataclass(item):
                        value[i] = TokenProcessor.find_and_replace_tokens(person, item)
                    elif isinstance(item, str):
                        value[i] = TokenProcessor.replace_token(item, person)

            elif is_dataclass(value):
                setattr(data_class, class_field.name, TokenProcessor.find_and_replace_tokens(person, value))

        return data_class

    @staticmethod
    def replace_token(text: str, person: Person) -> str:
        if not isinstance(text, str):
            return text

        pattern = r"\[\[.*?\]\]"
        all_tokens = re.findall(pattern, text, re.IGNORECASE)

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

                if (is_target_attribute or is_person_attribute) and key_to_find in attribute:
                    found_attribute = attribute
                    key_to_replace = key_to_find
                    break

            if not found_attribute:
                TokenProcessor.handle_token_not_found(parsed_token, token)

            replace_with = TokenProcessor.apply_formatting(found_attribute, key_to_replace, parsed_token.format)
            text = text.replace(token, str(replace_with))

        return text

    @staticmethod
    def handle_token_not_found(parsed_token, token):
        if parsed_token.attribute_level == "TARGET":
            raise ValueError(f"Invalid attribute name '{parsed_token.attribute_value}' in token '{token}'.")
        if parsed_token.attribute_level == "PERSON":
            raise ValueError(f"Invalid attribute name '{parsed_token.attribute_name}' in token '{token}'.")
        raise ValueError(f"Invalid attribute level '{parsed_token.attribute_level}' in token '{token}'.")

    @staticmethod
    def apply_formatting(attribute: dict[str, T], attribute_value: T, date_format: str | None) -> str:
        try:
            attribute_data = attribute.get(attribute_value)
            if (date_format or date_format == "") and attribute_data:
                replace_with_date_object = datetime.strptime(str(attribute_data), "%Y%m%d")
                replace_with = replace_with_date_object.strftime(str(date_format))
            else:
                replace_with = attribute_data if attribute_data else ""
            return replace_with
        except AttributeError:
            raise AttributeError("Invalid token format")
