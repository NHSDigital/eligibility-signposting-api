from __future__ import annotations

from wireup import service

from eligibility_signposting_api.model.person import Person


@service
class PersonDataReader:
    """Handles extracting and interpreting person data."""

    def get_person_cohorts(self, person: Person) -> set[str]:
        cohorts_row: Person = Person([])
        for data in person.data:
            if data.get("ATTRIBUTE_TYPE") == "COHORTS":
                cohorts_row.data.append(data)

        person_cohorts = set()

        if cohorts_row.data:
            for membership in cohorts_row.data[0].get("COHORT_MEMBERSHIPS", []):
                if membership.get("COHORT_LABEL"):
                    person_cohorts.add(membership.get("COHORT_LABEL"))

        return person_cohorts
