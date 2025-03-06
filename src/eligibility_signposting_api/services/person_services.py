import logging

from wireup import service

from eligibility_signposting_api.model.person import Name, Nickname
from eligibility_signposting_api.repos.exceptions import NotFoundError
from eligibility_signposting_api.repos.person_repo import PersonRepo

logger = logging.getLogger(__name__)


class UnknownPersonError(Exception):
    pass


@service
class PersonService:
    def __init__(self, person_repo: PersonRepo) -> None:
        super().__init__()
        self.person_repo = person_repo

    def get_nickname(self, name: Name | None = None) -> Nickname:
        if name:
            try:
                person = self.person_repo.get_person(name)
            except NotFoundError as e:
                raise UnknownPersonError from e
            else:
                return person.nickname
        return Nickname("World")
