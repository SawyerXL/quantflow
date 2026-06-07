"""
Cloudflare R2 storage service.

Free tier: 10 GB storage, 10M reads/month, 1M writes/month.
S3-compatible API via boto3.

Usage pattern (minimize storage):
    upload → backtest → read → delete
    Keep R2 usage at ~0 except during active backtests.
"""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

import boto3
from botocore.config import Config

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class R2Storage:
    """Cloudflare R2 object storage client (S3-compatible)."""

    def __init__(self):
        self._client = None
        self.bucket = settings.R2_BUCKET_NAME or "quantflow-uploads"

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 2, "mode": "standard"},
                    connect_timeout=10,
                    read_timeout=30,
                ),
                region_name="auto",
            )
        return self._client

    async def upload_csv(
        self,
        file_content: bytes,
        user_id: str,
        filename: str,
    ) -> str:
        """
        Upload a CSV file to R2.

        Returns the file key (path within bucket) for later retrieval.
        Files are stored under: uploads/{user_id}/{uuid}/{filename}
        """
        file_key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=file_content,
                ContentType="text/csv",
                Metadata={"user-id": user_id, "auto-delete": "true"},
            )
            logger.info("Uploaded CSV to R2: %s (%d bytes)", file_key, len(file_content))
            return file_key
        except Exception as exc:
            logger.error("R2 upload failed: %s", exc)
            raise RuntimeError(f"Failed to upload CSV: {exc}") from exc

    async def get_csv(self, file_key: str) -> bytes:
        """Retrieve a CSV file from R2."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=file_key)
            return response["Body"].read()
        except self.client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"CSV file not found: {file_key}")
        except Exception as exc:
            logger.error("R2 read failed for %s: %s", file_key, exc)
            raise RuntimeError(f"Failed to read CSV: {exc}") from exc

    async def delete_file(self, file_key: str) -> bool:
        """Delete a file from R2. Returns True if deleted."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_key)
            logger.info("Deleted from R2: %s", file_key)
            return True
        except Exception as exc:
            logger.warning("R2 delete failed for %s: %s", file_key, exc)
            return False

    async def list_user_files(self, user_id: str) -> list[str]:
        """List all file keys for a given user."""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=f"uploads/{user_id}/",
            )
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except Exception as exc:
            logger.warning("R2 list failed for user %s: %s", user_id, exc)
            return []


# Global singleton
r2_storage = R2Storage()
