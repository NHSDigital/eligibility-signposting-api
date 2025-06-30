import boto3
import botocore
import hashlib
import os

from dotenv import load_dotenv
load_dotenv()

class S3ConfigManager:
    def __init__(self, bucket_name: str, s3_prefix: str = ""):
        self.bucket_name = bucket_name
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client("s3")

    def _s3_key(self, filename: str) -> str:
        return os.path.join(self.s3_prefix, filename)

    def _calculate_file_hash(self, file_path: str) -> str:
        """SHA256 hash to compare local and S3 content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def upload_if_missing_or_changed(self, local_path: str):
        filename = os.path.basename(local_path)
        s3_key = self._s3_key(filename)

        try:
            if self.config_exists_and_matches(local_path, s3_key):
                print(f"✅ Config '{filename}' already exists and matches in S3. Skipping upload.")
                return
            else:
                print(f"🧹 Config '{filename}' exists in S3 but is different. Deleting old version...")
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except self.s3_client.exceptions.NoSuchKey:
            print(f"🆕 Config '{filename}' does not exist in S3. Proceeding to upload.")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                print(f"🆕 Config '{filename}' does not exist in S3. Proceeding to upload.")
            else:
                raise

        print(f"⬆️ Uploading new config '{filename}' to S3...")
        self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
        print(f"✅ Uploaded to s3://{self.bucket_name}/{s3_key}")



    def config_exists_and_matches(self, local_path: str, s3_key: str) -> bool:
        try:
            s3_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            s3_data = s3_obj["Body"].read()
            s3_hash = hashlib.sha256(s3_data).hexdigest()
            local_hash = self._calculate_file_hash(local_path)
            return s3_hash == local_hash
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return False
            raise
