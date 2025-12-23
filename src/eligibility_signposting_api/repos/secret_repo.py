import logging
from typing import Annotated, NewType

from botocore.client import BaseClient
from botocore.exceptions import ClientError
from wireup import Inject, service

logger = logging.getLogger(__name__)

SecretName = NewType("SecretName", str)


@service
class SecretRepo:
    def __init__(self, secret_manager: Annotated[BaseClient, Inject(qualifier="secretsmanager")]) -> None:
        super().__init__()
        self.secret_manager = secret_manager

    def _get_secret_by_stage(self, secret_name: str, stage: str) -> dict[str, str]:
        """Internal helper to fetch a secret by version stage."""
        try:
            response = self.secret_manager.get_secret_value(
                SecretId=secret_name,
                VersionStage=stage,
            )
            return {stage: response["SecretString"]}

        except ClientError:
            logger.warning("Failed to get secret %s at stage %s", secret_name, stage)
            return {}

    def get_secret_current(self, secret_name: str) -> dict[str, str]:
        return self._get_secret_by_stage(secret_name, "AWSCURRENT")

    def get_secret_previous(self, secret_name: str) -> dict[str, str]:
        return self._get_secret_by_stage(secret_name, "AWSPREVIOUS")
