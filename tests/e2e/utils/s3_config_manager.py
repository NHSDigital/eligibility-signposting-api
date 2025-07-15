import hashlib
import logging
import os
from pathlib import Path

import boto3
import botocore
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = logging.getLogger(__name__)


class S3ConfigManager:
    def __init__(self, bucket_name: str, s3_prefix: str = "") -> None:
        self.bucket_name: str = bucket_name
        self.s3_prefix: str = s3_prefix
        self.s3_client = boto3.client("s3")

    def _s3_key(self, filename: str) -> str:
        return str(Path(self.s3_prefix) / filename)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Return SHA256 hash of the given file."""
        sha256 = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def upload_if_missing_or_changed(self, local_path: Path) -> None:
        filename = Path(local_path).name
        s3_key = self._s3_key(filename)

        try:
            if self.config_exists_and_matches(local_path, s3_key):
                logger.info("\n🔍 Config '%s' already exists and matches in S3. Skipping upload.", filename)
                return
            logger.info("\n🧹 A different config exists under '%s/'. Deleting all existing files...", self.s3_prefix)
            self.delete_all_in_prefix()
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("\n🆕 No config found under '%s/'. Proceeding to upload.", self.s3_prefix)
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "NoSuchKey":
                logger.info("\n🆕 No config found under '%s/'. Proceeding to upload.", self.s3_prefix)
            else:
                raise

        logger.info("⬆️ Uploading new config '%s' to S3...", filename)
        self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
        logger.info("📄 Uploaded to s3://%s/%s", self.bucket_name, s3_key)

    def config_exists_and_matches(self, local_path: Path, s3_key: str) -> bool:
        session = boto3.Session()
        credentials = session.get_credentials()
        logger.info("AWS_ACCESS_KEY_ID = %s", credentials.access_key)
        logger.info("AWS_SECRET_ACCESS_KEY = %s", credentials.secret_key)
        logger.info("AWS_SESSION_TOKEN = %s", credentials.token)

        try:
            s3_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            s3_data = s3_obj["Body"].read()
            s3_hash = hashlib.sha256(s3_data).hexdigest()
            local_hash = self._calculate_file_hash(local_path)
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "NoSuchKey":
                return False
            raise
        else:
            return s3_hash == local_hash

    def delete_all_in_prefix(self) -> None:
        """Delete all S3 objects under the current prefix."""
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.s3_prefix)

        if "Contents" in response:
            to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
            self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": to_delete})
            logger.info("🗑️ Deleted %d file(s) under prefix '%s/'.", len(to_delete), self.s3_prefix)
        else:
            logger.info("📭 Nothing to delete under prefix '%s/'.", self.s3_prefix)

    def upload_all_configs(self, local_paths: list[Path]) -> None:
        desired_filenames = [p.name for p in local_paths]
        desired_keys = {self._s3_key(name) for name in desired_filenames}

        existing_keys = self._list_existing_keys()

        # Delete only unwanted ones (not in desired_keys)
        keys_to_delete = [key for key in existing_keys if key not in desired_keys]
        if keys_to_delete:
            self._delete_keys(keys_to_delete)

        for path in local_paths:
            filename = path.name
            s3_key = self._s3_key(filename)

            if self.config_exists_and_matches(path, s3_key):
                logger.info("✅ Config '%s' is unchanged in S3. Skipping upload.", filename)
            else:
                logger.info("⬆️ Uploading config '%s' to S3...", filename)
                self.s3_client.upload_file(path, self.bucket_name, s3_key)
                logger.info("📄 Uploaded to s3://%s/%s", self.bucket_name, s3_key)

    def _list_existing_keys(self) -> list[str]:
        """List all object keys under the current S3 prefix."""
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.s3_prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]

    def _delete_keys(self, keys: list[str]) -> None:
        """Delete specific keys from the S3 bucket."""
        self.s3_client.delete_objects(
            Bucket=self.bucket_name,
            Delete={"Objects": [{"Key": key} for key in keys]},
        )
        logger.info("🗑️ Deleted %d obsolete file(s): %s", len(keys), keys)


def upload_config_to_s3(local_path: Path) -> None:
    s3_connection = S3ConfigManager(os.getenv("S3_BUCKET_NAME"), os.getenv("S3_PREFIX"))
    s3_connection.upload_if_missing_or_changed(local_path)


def upload_configs_to_s3(config_filenames: list[str], config_path: str | Path) -> None:
    config_path = Path(config_path)
    local_paths = [config_path / f for f in config_filenames]
    s3_connection = S3ConfigManager(os.getenv("S3_BUCKET_NAME"), os.getenv("S3_PREFIX"))
    s3_connection.upload_all_configs(local_paths)


def delete_all_configs_from_s3() -> None:
    s3_connection = S3ConfigManager(os.getenv("S3_BUCKET_NAME"), os.getenv("S3_PREFIX"))
    s3_connection.delete_all_in_prefix()
