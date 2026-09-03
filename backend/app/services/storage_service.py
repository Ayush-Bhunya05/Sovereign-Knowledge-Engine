"""Local file-system storage service.

Designed with a consistent interface so that a future ``S3StorageService``
can be swapped in without touching callers.
"""

import shutil
from pathlib import Path

from fastapi import UploadFile


class LocalStorageService:
    """Store and retrieve uploaded files on the local file system."""

    def __init__(self, upload_dir: str) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: UploadFile, document_id: str, extension: str) -> str:
        """Persist *file* to disk and return the absolute storage path."""
        file_path = self.upload_dir / f"{document_id}{extension}"
        with open(file_path, "wb") as dest:
            shutil.copyfileobj(file.file, dest)
        return str(file_path.resolve())

    def retrieve(self, storage_path: str) -> bytes:
        """Read and return the raw bytes of a stored file."""
        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        return path.read_bytes()

    def delete(self, storage_path: str) -> bool:
        """Delete a stored file.  Returns ``True`` if the file existed."""
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, storage_path: str) -> bool:
        """Check whether a stored file exists."""
        return Path(storage_path).exists()
