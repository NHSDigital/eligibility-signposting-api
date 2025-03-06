from pydantic import BaseModel


class HelloResponse(BaseModel):
    status: int
    message: str


class Error(BaseModel):
    name: str
    reason: str


class Problem(BaseModel):
    """RFC 9457 problem detail - see https://pinboard.in/u:brunns/t:rfc-9457/"""

    type: str | None = None
    title: str | None = None
    status: int | None = None
    detail: str | None = None
    instance: str | None = None
    errors: list[Error] | None = None
