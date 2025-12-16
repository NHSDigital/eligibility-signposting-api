import logging
from typing import Annotated, Any, NewType

from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from wireup import Inject, service

from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.processors.hashing_service import HashingService
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

    def __init__(
        self,
        table: Annotated[Any, Inject(qualifier="person_table")],
        hashing_service: Annotated[HashingService, Inject()],
    ) -> None:
        super().__init__()
        self.table = table
        self._hashing_service = hashing_service

    def get_person_record(self, nhs_hash: str | None) -> Any:
        if nhs_hash:
            response = self.table.query(KeyConditionExpression=Key("NHS_NUMBER").eq(nhs_hash))

            items = response.get("Items", [])
            has_person = any(item.get("ATTRIBUTE_TYPE") == "PERSON" for item in items)

            if has_person:
                return items

        return None

    def get_eligibility_data(self, nhs_number: NHSNumber) -> Person:
        # Hash using AWSCURRENT secret and fetch items
        items = None
        nhs_hashed_with_current = self._hashing_service.hash_with_current_secret(nhs_number)
        if nhs_hashed_with_current:
            items = self.get_person_record(nhs_hashed_with_current)
            if not items:
                logger.warning("The AWSCURRENT secret was tried, but no person record was found")

        if not items:
            # Hash using AWSPREVIOUS secret and fetch items
            nhs_hashed_with_previous = self._hashing_service.hash_with_previous_secret(nhs_number)
            if nhs_hashed_with_previous:
                items = self.get_person_record(nhs_hashed_with_previous)
                if not items:
                    logger.error("The AWSPREVIOUS secret was also tried, but no person record was found")
                    message = "Person not found after checking AWSCURRENT and AWSPREVIOUS."
                    raise NotFoundError(message)
            else:
                # fallback : Fetch using Raw NHS number
                items = self.get_person_record(nhs_number)
                if not items:
                    logger.error("The not hashed nhs number was also tried, but no person record was found")
                    message = "Person not found after checking AWSCURRENT, AWSPREVIOUS, and not hashed NHS numbers."
                    raise NotFoundError(message)

        logger.info("Person record found")
        return Person(data=items)
