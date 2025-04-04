import logging
from typing import Annotated, Any

from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from wireup import Inject, service

from eligibility_signposting_api.model.eligibility import NHSNumber
from eligibility_signposting_api.repos.exceptions import NotFoundError

logger = logging.getLogger(__name__)


@service(qualifier="eligibility_table")
def eligibility_table_factory(dynamodb_resource: Annotated[ServiceResource, Inject(qualifier="dynamodb")]) -> Any:
    table = dynamodb_resource.Table("eligibility_data_store")  # type: ignore[reportAttributeAccessIssue]
    logger.info("eligibility_table %r", table, extra={"table": table})
    return table


@service
class EligibilityRepo:
    def __init__(self, table: Annotated[Any, Inject(qualifier="eligibility_table")]) -> None:
        super().__init__()
        self.table = table

    def get_person(self, nhs_number: NHSNumber) -> list[dict[str, Any]]:
        response = self.table.query(KeyConditionExpression=Key("NHS_NUMBER").eq(f"PERSON#{nhs_number}"))
        logger.debug("response %r for %r", response, nhs_number, extra={"response": response, "nhs_number": nhs_number})

        if not (items := response.get("Items")):
            message = f"Person not found with nhs_number {nhs_number}"
            raise NotFoundError(message)

        logger.debug("returning items %s", items, extra={"items": items})
        return items
