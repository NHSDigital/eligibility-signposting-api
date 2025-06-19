import logging
from typing import Annotated, Any, NewType

from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from wireup import Inject, service

from eligibility_signposting_api.model.eligibility import NHSNumber
from eligibility_signposting_api.repos.exceptions import NotFoundError

logger = logging.getLogger(__name__)

TableName = NewType("TableName", str)


@service(qualifier="person_table")
def person_table_factory(
    dynamodb_resource: Annotated[ServiceResource, Inject(qualifier="dynamodb")],
    person_table_name: Annotated[TableName, Inject(param="person_table_name")],
) -> Any:
    table = dynamodb_resource.Table(person_table_name)  # type: ignore[reportAttributeAccessIssue]
    logger.info("person_table %r", table, extra={"table": table})
    return table


@service
class PersonRepo:
    """Repository class for the data held about a person which may be relevant to calculating their eligibility for
    vaccination.

    This data is held in a handful of records in a single Dynamodb table.
    """

    def __init__(self, table: Annotated[Any, Inject(qualifier="person_table")]) -> None:
        super().__init__()
        self.table = table

    def get_eligibility_data(self, nhs_number: NHSNumber) -> list[dict[str, Any]]:
        response = self.table.query(KeyConditionExpression=Key("NHS_NUMBER").eq(nhs_number))
        logger.debug("response %r for %r", response, nhs_number, extra={"response": response, "nhs_number": nhs_number})

        if not (items := response.get("Items")):
            message = f"Person not found with nhs_number {nhs_number}"
            raise NotFoundError(message)

        logger.debug("returning items %s", items, extra={"items": items})
        return items
