import logging
from typing import Annotated, Any, NewType

from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from wireup import Inject, service

from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.repos.exceptions import NotFoundError

import hashlib
import hmac

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

    def __init__(self,
                 table: Annotated[Any, Inject(qualifier="person_table")],
                 hmac_key: Annotated[bytes, Inject(qualifier="nhs_hmac_key")],
                 ) -> None:
        super().__init__()
        self.table = table
        self._hmac_key = hmac_key

    def _hash_nhs_number(self, nhs_number: NHSNumber) -> str:
        nhs_str = str(nhs_number)

        digest = hmac.new(
            self._hmac_key,
            nhs_str.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

        return digest

    def get_eligibility_data(self, nhs_number: NHSNumber) -> Person:
        nhs_hash = self._hash_nhs_number(nhs_number)

        # response = self.table.query(KeyConditionExpression=Key("NHS_NUMBER").eq(nhs_number))
        response = self.table.query(KeyConditionExpression=Key("NHS_NUMBER").eq(nhs_hash))

        if not (items := response.get("Items")) or not next(
            (item for item in items if item.get("ATTRIBUTE_TYPE") == "PERSON"), None
        ):
            message = f"Person not found with nhs_number {nhs_number}"
            raise NotFoundError(message)

        return Person(data=items)
