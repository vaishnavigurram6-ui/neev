"""Private local artifact storage. No user-controlled paths; no public mount."""
from io import BytesIO
from pathlib import Path
import warnings
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.settings import get_settings

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def read_upload(upload: UploadFile, *, image_only: bool = False) -> tuple[bytes, str]:
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Each file must be at most 10 MB.")
    if not data:
        raise HTTPException(422, "Empty files are not accepted.")
    if not image_only and upload.content_type == "application/pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise HTTPException(422, "Invalid PDF envelope.")
        return data, "application/pdf"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Unsupported image format")
                mime = Image.MIME[image.format]
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
        return data, mime
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise HTTPException(422, "Upload a valid PDF, JPEG, PNG or WebP image." if not image_only
                            else "Upload a valid JPEG, PNG or WebP image.") from None


def store_artifact(data: bytes) -> str:
    root = Path(get_settings().artifact_dir)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / uuid4().hex
    # Exclusive creation prevents accidental overwrite. Restrict loan evidence.
    import os
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
        handle.write(data)
    return str(path.resolve())


def read_artifact(reference: str) -> bytes:
    root = Path(get_settings().artifact_dir).resolve()
    path = Path(reference).resolve()
    if path.parent != root or len(path.name) != 32:
        raise ValueError("Invalid artifact reference")
    return path.read_bytes()