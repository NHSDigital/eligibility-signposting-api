from collections.abc import Sequence
from datetime import date
from random import choice, shuffle
from typing import Any, Literal, get_args

from faker import Faker

from tests.conftest import PersonDetailProvider

Gender = Literal["0", "1", "2", "9"]  # 0 - Not known, 1- Male, 2 - Female, 9 - Not specified. I know, right?


def person_rows_builder(  # noqa:PLR0913
    nhs_number: str,
    *,
    date_of_birth: date | None = ...,
    gender: Gender | None = ...,
    postcode: str | None = ...,
    cohorts: Sequence[str] | None = ...,
    vaccines: Sequence[tuple[str, date]] | None = ...,
    icb: str | None = ...,
    gp_practice: str | None = ...,
    pcn: str | None = ...,
    comissioning_region: str | None = ...,
    thirteen_q: bool | None = ...,
    care_home: bool | None = ...,
    de: bool | None = ...,
    msoa: str | None = ...,
    lsoa: str | None = ...,
) -> list[dict[str, Any]]:
    faker = Faker("en_UK")
    faker.add_provider(PersonDetailProvider)

    key = f"PERSON#{nhs_number}"
    date_of_birth = date_of_birth if date_of_birth is not ... else faker.date_of_birth(minimum_age=18, maximum_age=99)
    gender = gender if gender is not ... else choice(get_args(Gender))
    postcode = postcode if postcode is not ... else faker.postcode()
    cohorts = cohorts if cohorts is not ... else ["cohort-a", "cohort-b"]
    vaccines = vaccines if vaccines is not ... else [("RSV", faker.past_date("-5y")), ("COVID", faker.past_date("-5y"))]
    icb = icb if icb is not ... else faker.icb()
    gp_practice = gp_practice if gp_practice is not ... else faker.gp_practice()
    pcn = pcn if pcn is not ... else faker.pcn()
    comissioning_region = comissioning_region if comissioning_region is not ... else faker.comissioning_region()
    thirteen_q = thirteen_q if thirteen_q is not ... else faker.boolean()
    care_home = care_home if care_home is not ... else faker.boolean()
    de = de if de is not ... else faker.boolean()
    msoa = msoa if msoa is not ... else faker.msoa()
    lsoa = lsoa if lsoa is not ... else faker.lsoa()
    rows: list[dict[str, Any]] = [
        {
            "NHS_NUMBER": key,
            "ATTRIBUTE_TYPE": "PERSON",
            "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            "GENDER": gender,
            "POSTCODE": postcode,
            "ICB": icb,
            "GP_PRACTICE": gp_practice,
            "PCN": pcn,
            "COMISSIONING_REGION": comissioning_region,
            "13Q_FLAG": "Y" if thirteen_q else "N",
            "CARE_HOME_FLAG": "Y" if care_home else "N",
            "DE_FLAG": "Y" if de else "N",
            "MSOA": msoa,
            "LSOA": lsoa,
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
            "LAST_SUCCESSFUL_DATE": (
                last_successful_date.strftime("%Y%m%d") if last_successful_date else last_successful_date
            ),
            "OPTOUT": choice(["Y", "N"]),
            "LAST_INVITE_DATE": faker.past_date("-5y").strftime("%Y%m%d"),
        }
        for vaccine, last_successful_date in vaccines
    )

    shuffle(rows)
    return rows
