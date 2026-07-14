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
    if len(data) > settings.max_upload_size_bytes:
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


def download_file(path: str) -> tuple[bytes, str]:
    """
    Download a file from Supabase Storage.
    Returns (file_bytes, mime_type).
    Used by the reextract endpoint to re-run AI on the original upload.
    """
    try:
        data = _supabase.storage.from_(settings.STORAGE_BUCKET).download(path)
    except Exception as exc:
        logger.exception("Storage download failed for path %s", path)
        raise StorageError("Could not retrieve the file.") from exc

    ext = path.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp", "heic": "image/heic", "heif": "image/heif",
                "pdf": "application/pdf"}
    mime_type = mime_map.get(ext, "application/octet-stream")
    return data, mime_type


def get_public_url(path: str) -> str:
    return _supabase.storage.from_(settings.STORAGE_BUCKET).get_public_url(path)


def delete_file(path: str) -> None:
    try:
        _supabase.storage.from_(settings.STORAGE_BUCKET).remove([path])
    except Exception as exc:
        logger.exception("Storage delete failed for path %s", path)
        raise StorageError("Could not delete the file from storage.") from exc


def get_thumbnail_url(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    if ext in ("jpg", "jpeg", "png", "webp", "heic", "heif"):
        return f"{settings.SUPABASE_URL}/storage/v1/render/image/public/{settings.STORAGE_BUCKET}/{path}?width=200&height=200&resize=cover"
    return get_public_url(path)