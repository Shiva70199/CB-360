"""Dataset file storage.

Local disk is used in development. Production on Vercel cannot keep files, so
uploads require an S3-compatible bucket. Restaurant analytics read the database
and do not use this storage.
"""

from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status

from app.config import settings

PERSISTENT_STORAGE_DETAIL = (
    "Dataset uploads are not kept on the Vercel filesystem. "
    "Set STORAGE_BACKEND=s3, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, "
    "and S3_ENDPOINT_URL when the bucket is not AWS. "
    "Restaurant analytics use Neon and do not need this storage."
)


def _require_persistent_storage() -> None:
    if settings.object_storage_configured():
        return
    if settings.is_production():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PERSISTENT_STORAGE_DETAIL,
        )


def _s3_client():
    import boto3

    kwargs = {
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
        "region_name": settings.s3_region or "us-east-1",
    }
    if settings.s3_endpoint_url.strip():
        kwargs["endpoint_url"] = settings.s3_endpoint_url.strip()
    return boto3.client("s3", **kwargs)


def _object_key(user_id: int, dataset_id: int) -> str:
    return f"datasets/{user_id}/{dataset_id}.csv"


def save_dataset_csv(user_id: int, dataset_id: int, df: pd.DataFrame) -> str:
    _require_persistent_storage()
    if settings.object_storage_configured():
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        key = _object_key(user_id, dataset_id)
        _s3_client().put_object(
            Bucket=settings.s3_bucket.strip(),
            Key=key,
            Body=buffer.getvalue(),
            ContentType="text/csv",
        )
        return f"s3://{settings.s3_bucket.strip()}/{key}"

    upload_root = settings.resolve_upload_dir()
    upload_root.mkdir(parents=True, exist_ok=True)
    user_dir = upload_root / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / f"{dataset_id}.csv"
    df.to_csv(file_path, index=False)
    return str(file_path)


def load_dataset_csv(file_path: str) -> pd.DataFrame:
    if file_path.startswith("s3://"):
        if not settings.object_storage_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=PERSISTENT_STORAGE_DETAIL,
            )
        without_scheme = file_path[len("s3://") :]
        bucket, _, key = without_scheme.partition("/")
        if not bucket or not key:
            raise HTTPException(status_code=404, detail="Dataset file not found.")
        response = _s3_client().get_object(Bucket=bucket, Key=key)
        return pd.read_csv(BytesIO(response["Body"].read()))

    from pathlib import Path

    candidate = Path(file_path)
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found.")
    try:
        return pd.read_csv(candidate)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read dataset file.") from None


def delete_dataset_file(file_path: str | None) -> None:
    if not file_path:
        return
    if file_path.startswith("s3://"):
        if not settings.object_storage_configured():
            return
        without_scheme = file_path[len("s3://") :]
        bucket, _, key = without_scheme.partition("/")
        if bucket and key:
            _s3_client().delete_object(Bucket=bucket, Key=key)
        return
    from pathlib import Path

    candidate = Path(file_path)
    if candidate.exists():
        candidate.unlink()
