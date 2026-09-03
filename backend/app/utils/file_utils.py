"""File validation and classification utilities."""

import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Extension → document type mapping
# ---------------------------------------------------------------------------

EXTENSION_TO_DOCUMENT_TYPE: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".txt": "txt",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tiff": "image",
    ".tif": "image",
    ".bmp": "image",
}

ALLOWED_EXTENSIONS: set[str] = set(EXTENSION_TO_DOCUMENT_TYPE.keys())


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_file_extension(filename: str | None) -> str:
    """Extract and normalise the file extension.

    Raises ``ValueError`` if the filename is missing or has no extension.
    """
    if not filename:
        raise ValueError("Filename is required")
    ext = Path(filename).suffix.lower()
    if not ext:
        raise ValueError(f"Filename '{filename}' has no extension")
    return ext


def get_document_type(extension: str) -> str:
    """Map a file extension to its logical document type.

    Raises ``ValueError`` for unsupported extensions.
    """
    doc_type = EXTENSION_TO_DOCUMENT_TYPE.get(extension)
    if doc_type is None:
        raise ValueError(
            f"Unsupported file extension: '{extension}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return doc_type


def validate_file_type(filename: str | None) -> tuple[str, str]:
    """Validate that the uploaded file has an allowed extension.

    Returns ``(extension, document_type)`` on success.
    Raises ``ValueError`` on failure.
    """
    extension = get_file_extension(filename)
    document_type = get_document_type(extension)
    return extension, document_type


def validate_file_size(file_size: int, max_size_bytes: int) -> None:
    """Raise ``ValueError`` if *file_size* exceeds *max_size_bytes*."""
    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"File size ({file_mb:.1f} MB) exceeds maximum allowed ({max_mb:.1f} MB)"
        )


def generate_document_id() -> uuid.UUID:
    """Generate a new unique document identifier."""
    return uuid.uuid4()
