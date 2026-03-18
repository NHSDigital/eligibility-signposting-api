import json
import logging
from typing import Annotated

from aws_xray_sdk.core import xray_recorder
from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.config.config import AwsKinesisFirehoseStreamName
from eligibility_signposting_api.config.config import AwsKinesisStreamName

logger = logging.getLogger(__name__)


@service
class AuditService:  # pragma: no cover
    def __init__(
        self,
        kinesis: Annotated[BaseClient, Inject(qualifier="kinesis")],
        audit_delivery_stream: Annotated[AwsKinesisStreamName, Inject(param="kinesis_audit_stream")],
    ) -> None:
        super().__init__()
        self.kinesis = kinesis
        self.audit_delivery_stream = audit_delivery_stream

    @xray_recorder.capture("AuditService.audit")  # pyright: ignore[reportCallIssue]
    def audit(self, audit_record: dict) -> None:
        """
        Sends an audit record to the configured Firehose delivery stream.

        Args:
            audit_record (dict): The audit data to send.

        Returns:
            str: The Firehose record ID.
        """
        data = json.dumps(audit_record, default=str)
        response = self.kinesis.put_record(
            StreamName=self.audit_delivery_stream,
            Data=(data + "\n").encode("utf-8"),
            PartitionKey="audit",
        )
        logger.info("Successfully sent to kinesis")
