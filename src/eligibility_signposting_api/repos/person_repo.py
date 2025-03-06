import logging
from typing import Any

from boto3.resources.base import ServiceResource
from wireup import service

from eligibility_signposting_api.model.person import Name, Person
from eligibility_signposting_api.repos.exceptions import NotFoundError

logger = logging.getLogger(__name__)


@service
def people_table_factory(dynamodb_resource: ServiceResource) -> Any:
    table = dynamodb_resource.Table("People")  # type: ignore[reportAttributeAccessIssue]
    logger.info("built people_table: %r", table)
    return table


@service
class PersonRepo:
    def __init__(self, people_table: Any) -> None:
        super().__init__()
        self.people_table = people_table

    def get_person(self, name: Name) -> Person:
        dynamo_response = self.people_table.get_item(Key={"name": name})

        if "Item" not in dynamo_response:
            message = f"Person not found with name {name}"
            raise NotFoundError(message)

        return Person.model_validate(dynamo_response.get("Item"))
