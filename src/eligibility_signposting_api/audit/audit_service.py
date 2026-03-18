import json
import logging
from typing import Annotated

from aws_xray_sdk.core import xray_recorder
from botocore.client import BaseClient
from wireup import Inject, service

from eligibility_signposting_api.config.config import AwsKinesisStreamName

logger = logging.getLogger(__name__)


@service
class AuditService:  # pragma: no cover
    def __init__(
        self,
        kinesis: Annotated[BaseClient, Inject(qualifier="kinesis")],
        audit_stream: Annotated[AwsKinesisStreamName, Inject(param="kinesis_audit_stream")],
    ) -> None:
        super().__init__()
        self.kinesis = kinesis
        self.audit_stream = audit_stream

    @xray_recorder.capture("AuditService.audit")  # pyright: ignore[reportCallIssue]
    def audit(self, audit_record: dict) -> None:
        """
        Sends an audit record to the configured kinesis data stream.

        Args:
            audit_record (dict): The audit data to send.
        """
        data = json.dumps(audit_record, default=str)
        response = self.kinesis.put_record(
            StreamName=self.audit_stream,
            Data=(data + "\n").encode("utf-8"),
            PartitionKey="audit",
        )
        logger.info("Successfully sent to kinesis", extra={
            "stream_name": self.audit_stream,
            "kinesis_sequence_number": response.get("SequenceNumber"),
            "kinesis_shard_id": response.get("ShardId"),
        },)
