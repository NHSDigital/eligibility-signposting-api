import json
import logging
from typing import Annotated

from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.config.config import AwsKinesisFirehoseStreamName

logger = logging.getLogger(__name__)


@service
class AuditService:  # pragma: no cover
    def __init__(
        self,
        firehose: Annotated[BaseClient, Inject(qualifier="firehose")],
        audit_delivery_stream: Annotated[AwsKinesisFirehoseStreamName, Inject(param="kinesis_audit_stream_to_s3")],
    ) -> None:
        super().__init__()
        self.firehose = firehose
        self.audit_delivery_stream = audit_delivery_stream

    def audit(self, audit_record: dict) -> None:
        """
        Sends an audit record to the configured Firehose delivery stream.

        Args:
            audit_record (dict): The audit data to send.

        Returns:
            str: The Firehose record ID.
        """
        response = self.firehose.put_record(
            DeliveryStreamName=self.audit_delivery_stream,
            Record={"Data": (json.dumps(audit_record) + "\n").encode("utf-8")},
        )
        logger.info("Successfully sent to the Firehose", extra={"firehose_record_id": response["RecordId"]})
