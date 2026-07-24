"""Artifact reads/writes on B2 (manifest JSON, SQL dump, dedup result logs).

Kept out of `b2_client.py` (which sits at the 300-line ceiling). boto3 stays
confined to the repo/ layer; the cached S3 client is reused from `b2_client`
for connection pooling.
"""

import io
import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import _invalidate_list_cache, get_s3_client


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Write raw bytes to B2 under `key`. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()  # a new artifact must show up in listings/stats


def put_json(key: str, obj: dict | list) -> None:
    """Write a JSON document to B2 under `key`."""
    payload = json.dumps(obj, indent=2, default=str).encode("utf-8")
    put_bytes(key, payload, content_type="application/json")


def get_inline_url(key: str, content_type: str | None = None, expires_in: int = 3600) -> str:
    """Presigned GET URL with `inline` disposition — suitable as an `<audio>`
    `src` so the track plays in the browser instead of downloading. Raises
    RuntimeError on failure."""
    client = get_s3_client()
    params: dict = {
        "Bucket": settings.b2_bucket_name,
        "Key": key,
        "ResponseContentDisposition": "inline",
    }
    if content_type:
        params["ResponseContentType"] = content_type
    try:
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def get_json(key: str) -> dict | list | None:
    """Read a JSON document from B2, or None if the object doesn't exist.

    Raises RuntimeError on any non-404 S3 failure.
    """
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e
