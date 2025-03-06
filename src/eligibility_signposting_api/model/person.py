from typing import NewType

from pydantic import BaseModel

Name = NewType("Name", str)
Nickname = NewType("Nickname", str)


class Person(BaseModel):
    name: Name
    nickname: Nickname
