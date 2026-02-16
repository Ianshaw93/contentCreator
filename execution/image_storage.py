"""
Image library - S3-backed shared image pool.
Images are stored in S3 and tracked via PostgreSQL metadata.
Drafts reference library images by ID (attach/detach).
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from s3_storage import upload_bytes, delete_object, ensure_bucket
from database import SessionLocal, Image

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _image_to_dict(row: Image) -> dict:
    return {
        "id": row.id,
        "original_name": row.original_name,
        "s3_key": row.s3_key,
        "url": row.url,
        "uploaded_at": row.uploaded_at,
    }


def save_image(file_content: bytes, original_filename: str) -> dict:
    """
    Upload an image to S3 and add to library.

    Args:
        file_content: Binary image data
        original_filename: Original filename from upload

    Returns:
        Image metadata dict with id, original_name, s3_key, url, uploaded_at
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {ext}")

    image_id = str(uuid.uuid4())[:8]
    s3_key = f"library/{image_id}{ext}"
    content_type = CONTENT_TYPES.get(ext, "image/jpeg")

    ensure_bucket()
    url = upload_bytes(s3_key, file_content, content_type)

    entry = Image(
        id=image_id,
        original_name=original_filename,
        s3_key=s3_key,
        url=url,
        uploaded_at=datetime.now().isoformat(),
    )

    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _image_to_dict(entry)


def delete_image(image_id: str) -> bool:
    """Delete an image from S3 and library."""
    with SessionLocal() as db:
        row = db.query(Image).filter(Image.id == image_id).first()
        if not row:
            return False
        delete_object(row.s3_key)
        db.delete(row)
        db.commit()
        return True


def list_images() -> list[dict]:
    """Return all library images."""
    with SessionLocal() as db:
        rows = db.query(Image).order_by(Image.uploaded_at.desc()).all()
        return [_image_to_dict(r) for r in rows]


def get_image(image_id: str) -> Optional[dict]:
    """Get a single image by ID."""
    with SessionLocal() as db:
        row = db.query(Image).filter(Image.id == image_id).first()
        return _image_to_dict(row) if row else None


def get_image_url(image_id: str) -> Optional[str]:
    """Get the S3 URL for an image."""
    img = get_image(image_id)
    if img:
        return img["url"]
    return None
