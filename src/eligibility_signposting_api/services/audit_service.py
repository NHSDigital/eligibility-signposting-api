import json
import logging
from typing import Annotated

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.config.contants import ELIGIBILITY_SIGNPOSTING_AUDIT_STREAM

logger = logging.getLogger(__name__)


@service
class AuditService:
    def __init__(self, firehose: Annotated[BaseClient, Inject(qualifier="firehose")]) -> None:
        super().__init__()
        self.firehose = firehose
        self.delivery_stream_name = ELIGIBILITY_SIGNPOSTING_AUDIT_STREAM

    def audit(self, audit_record: dict) -> None:
        """
        Sends an audit record to the configured Firehose delivery stream.

        Args:
            audit_record (dict): The audit data to send.

        Returns:
            str: The Firehose record ID.
        """
        response = self.firehose.put_record(
            DeliveryStreamName=self.delivery_stream_name,
            Record={"Data": (json.dumps(audit_record) + "\n").encode("utf-8")},
        )
        logger.info("Successfully sent to the Firehose", extra={"firehose_record_id": response["RecordId"]})
