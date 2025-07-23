from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from wireup import service

Row = Collection[Mapping[str, Any]]


@service
class PersonDataReader:
    """Handles extracting and interpreting person data."""

    def get_person_cohorts(self, person_data: Row) -> set[str]:
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (row for row in person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"),
            {},
        )
        return set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

