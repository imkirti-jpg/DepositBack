from __future__ import annotations
import logging
import uuid
from fastapi import UploadFile
from supabase import create_client
from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

_ALLOWED_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
    "application/pdf": "pdf",
}


class StorageError(Exception):
    pass


async def upload_file(file: UploadFile, *, property_id: str, category: str) -> str:
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise StorageError(f"File type '{content_type}' not accepted. Upload a JPEG, PNG, WebP, HEIC, or PDF.")

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_MB:
        raise StorageError(f"File too large. Maximum is {settings.MAX_UPLOAD_SIZE_MB} MB.")
    if len(data) == 0:
        raise StorageError("The uploaded file is empty.")

    ext = _ALLOWED_TYPES[content_type]
    path = f"{property_id}/{category}/{uuid.uuid4()}.{ext}"

    try:
        _supabase.storage.from_(settings.STORAGE_BUCKET).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except Exception as exc:
        logger.exception("Storage upload failed for path %s", path)
        raise StorageError("Could not save the file. Please try again.") from exc

    logger.info("Uploaded %s (%d bytes) → %s", file.filename, len(data), path)
    return path


def get_public_url(path: str) -> str:
    return _supabase.storage.from_(settings.STORAGE_BUCKET).get_public_url(path)