from dataclasses import dataclass
from typing import Any


@dataclass
class Person:
    data: list[dict[str, Any]]
