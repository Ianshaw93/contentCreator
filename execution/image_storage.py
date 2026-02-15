"""
Image library - S3-backed shared image pool.
Images are stored in S3 and tracked via .image_library.json metadata file.
Drafts reference library images by ID (attach/detach).
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from s3_storage import upload_bytes, delete_object, ensure_bucket

LIBRARY_FILE = Path(__file__).parent.parent / ".image_library.json"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _load_library() -> list[dict]:
    if not LIBRARY_FILE.exists():
        return []
    with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("images", [])


def _save_library(images: list[dict]) -> None:
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump({"images": images}, f, indent=2, default=str)


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

    entry = {
        "id": image_id,
        "original_name": original_filename,
        "s3_key": s3_key,
        "url": url,
        "uploaded_at": datetime.now().isoformat(),
    }

    images = _load_library()
    images.insert(0, entry)
    _save_library(images)

    return entry


def delete_image(image_id: str) -> bool:
    """Delete an image from S3 and library."""
    images = _load_library()

    for i, img in enumerate(images):
        if img["id"] == image_id:
            delete_object(img["s3_key"])
            images.pop(i)
            _save_library(images)
            return True

    return False


def list_images() -> list[dict]:
    """Return all library images."""
    return _load_library()


def get_image(image_id: str) -> Optional[dict]:
    """Get a single image by ID."""
    for img in _load_library():
        if img["id"] == image_id:
            return img
    return None


def get_image_url(image_id: str) -> Optional[str]:
    """Get the S3 URL for an image."""
    img = get_image(image_id)
    if img:
        return img["url"]
    return None
