import random
from collections.abc import Sequence
from typing import Any

from faker import Faker

from eligibility_signposting_api.model import eligibility
from eligibility_signposting_api.model.eligibility import DateOfBirth


def eligibility_rows(
    faker: Faker,
    nhs_number: eligibility.NHSNumber,
    *,
    date_of_birth: eligibility.DateOfBirth | None = None,
    cohorts: Sequence[str] | None = None,
    vaccines: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    key = f"PERSON#{nhs_number}"
    date_of_birth = date_of_birth or DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=99))
    postcode = eligibility.Postcode(faker.postcode())
    cohorts = cohorts if cohorts is not None else ["cohort-a", "cohort-b"]
    vaccines = vaccines if vaccines is not None else ["RSV", "COVID"]
    rows: list[dict[str, Any]] = [
        {
            "NHS_NUMBER": key,
            "ATTRIBUTE_TYPE": "PERSON",
            "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            "POSTCODE": postcode,
        },
        {
            "NHS_NUMBER": key,
            "ATTRIBUTE_TYPE": "COHORTS",
            "COHORT_MAP": {
                "cohorts": {
                    "M": {
                        cohort: {"M": {"dateJoined": {"S": faker.past_date().strftime("%Y%m%d")}}} for cohort in cohorts
                    }
                }
            },
        },
    ]
    rows.extend(
        {
            "NHS_NUMBER": key,
            "ATTRIBUTE_TYPE": vaccine,
            "LAST_SUCCESSFUL_DATE": faker.past_date().strftime("%Y%m%d"),
            "OPTOUT": random.choice(["Y", "N"]),
            "LAST_INVITE_DATE": faker.past_date().strftime("%Y%m%d"),
        }
        for vaccine in vaccines
    )

    return rows
