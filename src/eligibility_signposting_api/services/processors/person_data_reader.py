from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from wireup import service

Row = Collection[Mapping[str, Any]]


@service
class PersonDataReader:
    """Handles extracting and interpreting person data."""

    def get_person_cohorts(self, person_data: Row) -> set[str]:
        cohorts_row: Mapping[str, list[dict[str, str]]] = next(
            (row for row in person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"),
            {},
        )
        person_cohorts = set()

        for membership in cohorts_row.get("COHORT_MEMBERSHIPS", []):
            if membership.get("COHORT_LABEL"):
                person_cohorts.add(membership.get("COHORT_LABEL"))

        return person_cohorts
