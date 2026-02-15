"""
S3-compatible storage helpers for image upload/delete/URL.
Works with MinIO on Railway or any S3-compatible service.
"""
import os
import boto3
from botocore.config import Config


def _get_client():
    """Get a configured S3 client."""
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    region = os.getenv("S3_REGION", "us-east-1")

    if not all([endpoint_url, access_key, secret_key]):
        raise RuntimeError(
            "S3 not configured. Set S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY env vars."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def _get_bucket() -> str:
    return os.getenv("S3_BUCKET", "images")


def ensure_bucket():
    """Create the bucket if it doesn't exist."""
    client = _get_client()
    bucket = _get_bucket()
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=bucket)


def upload_bytes(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """
    Upload bytes to S3 and return the public URL.

    Args:
        key: S3 object key (e.g. "abc123.jpg")
        data: File bytes
        content_type: MIME type

    Returns:
        Public URL for the object
    """
    client = _get_client()
    bucket = _get_bucket()

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        ACL="public-read",
    )

    endpoint = os.getenv("S3_ENDPOINT_URL", "").rstrip("/")
    return f"{endpoint}/{bucket}/{key}"


def delete_object(key: str) -> bool:
    """Delete an object from S3."""
    client = _get_client()
    bucket = _get_bucket()
    try:
        client.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def download_bytes(key: str) -> bytes:
    """Download an object's bytes from S3."""
    client = _get_client()
    bucket = _get_bucket()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def get_public_url(key: str) -> str:
    """Get the public URL for an S3 object."""
    endpoint = os.getenv("S3_ENDPOINT_URL", "").rstrip("/")
    bucket = _get_bucket()
    return f"{endpoint}/{bucket}/{key}"
