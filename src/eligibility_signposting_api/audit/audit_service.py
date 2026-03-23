import hashlib
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

    @staticmethod
    def get_partition_key(response_id: str) -> str:
        h = int(hashlib.sha256(response_id.encode()).hexdigest(), 16)
        bucket = h % 32
        return f"audit-{bucket:02d}"

    @xray_recorder.capture("AuditService.audit")  # pyright: ignore[reportCallIssue]
    def audit(self, audit_record: dict) -> None:
        """
        Sends an audit record to the configured kinesis data stream.

        Args:
            audit_record (dict): The audit data to send.
        """
        data = json.dumps(audit_record, default=str)
        response_id = audit_record.get("response", {}).get("responseId")
        if response_id is None:
            response_id = str(uuid.uuid4())
            logger.warning("Missing responseId in audit record; using UUID fallback")
        partition_key = self.get_partition_key(str(response_id))
        response = self.kinesis.put_record(
            StreamName=self.audit_stream,
            Data=(data + "\n").encode("utf-8"),
            PartitionKey=partition_key,
        )
        logger.info(
            "Successfully sent to kinesis",
            extra={
                "stream_name": self.audit_stream,
                "kinesis_sequence_number": response.get("SequenceNumber"),
                "kinesis_shard_id": response.get("ShardId"),
            },
        )
