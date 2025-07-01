import os
import hashlib
import boto3
import botocore
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class S3ConfigManager:
    def __init__(self, bucket_name: str, s3_prefix: str = "") -> None:
        self.bucket_name: str = bucket_name
        self.s3_prefix: str = s3_prefix
        self.s3_client = boto3.client("s3")

    def _s3_key(self, filename: str) -> str:
        return os.path.join(self.s3_prefix, filename)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Return SHA256 hash of the given file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def upload_if_missing_or_changed(self, local_path: str) -> None:
        filename = os.path.basename(local_path)
        s3_key = self._s3_key(filename)

        try:
            if self.config_exists_and_matches(local_path, s3_key):
                print(
                    f"\n🔍 Config '{filename}' already exists and matches in S3. "
                    "Skipping upload."
                )
                return
            print(
                f"\n🧹 A different config exists under '{self.s3_prefix}/'. "
                "Deleting all existing files..."
            )
            self._delete_all_in_prefix()
        except self.s3_client.exceptions.NoSuchKey:
            print(f"\n🆕 No config found under '{self.s3_prefix}/'. Proceeding to upload.")
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "NoSuchKey":
                print(f"\n🆕 No config found under '{self.s3_prefix}/'. Proceeding to upload.")
            else:
                raise

        print(f"⬆️ Uploading new config '{filename}' to S3...")
        self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
        print(f"📄 Uploaded to s3://{self.bucket_name}/{s3_key}")

    def config_exists_and_matches(self, local_path: str, s3_key: str) -> bool:
        try:
            s3_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            s3_data = s3_obj["Body"].read()
            s3_hash = hashlib.sha256(s3_data).hexdigest()
            local_hash = self._calculate_file_hash(local_path)
            return s3_hash == local_hash
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "NoSuchKey":
                return False
            raise

    def _delete_all_in_prefix(self) -> None:
        """Delete all S3 objects under the current prefix."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=self.s3_prefix
        )

        if "Contents" in response:
            to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={"Objects": to_delete}
            )
            print(f"🗑️ Deleted {len(to_delete)} file(s) under prefix '{self.s3_prefix}/'.")
        else:
            print(f"📭 Nothing to delete under prefix '{self.s3_prefix}/'.")
