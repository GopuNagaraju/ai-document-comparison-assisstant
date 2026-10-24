"""
PDF Document Reader and Validator Module.
Handles PDF validation, page-by-page text extraction using pypdf,
character/page counts, content previews, and input length checks.
"""

import io
from typing import Dict, Any, List, Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError

# Default character threshold before warning/chunking (approx. 30,000 tokens)
MAX_SAFE_CHARS = 120000
PREVIEW_CHAR_LIMIT = 600


class DocumentValidationError(Exception):
    """Raised when an uploaded file fails validation."""
    pass


def validate_and_extract_pdf(
    file_obj: Any,
    filename: str = "document.pdf",
    max_chars: int = MAX_SAFE_CHARS
) -> Dict[str, Any]:
    """
    Validates an uploaded PDF file and extracts text page by page.

    Args:
        file_obj: File-like object or bytes representing the uploaded PDF.
        filename: Name of the uploaded file.
        max_chars: Maximum character limit before truncation/chunking warning.

    Returns:
        Dictionary containing:
            - filename (str)
            - is_valid (bool)
            - error_message (Optional[str])
            - page_count (int)
            - readable_pages (int)
            - unreadable_pages (List[int])
            - char_count (int)
            - word_count (int)
            - full_text (str): Text formatted with [Page X] markers for traceability.
            - preview_text (str): Short preview of extracted content.
            - is_truncated (bool): True if document exceeded max_chars.
            - limitations_note (Optional[str]): Note on unreadable pages or truncation.
    """
    result: Dict[str, Any] = {
        "filename": filename,
        "is_valid": False,
        "error_message": None,
        "page_count": 0,
        "readable_pages": 0,
        "unreadable_pages": [],
        "char_count": 0,
        "word_count": 0,
        "full_text": "",
        "preview_text": "",
        "is_truncated": False,
        "limitations_note": None,
    }

    # FR-02: Validate file extension
    if not filename or not filename.lower().endswith(".pdf"):
        result["error_message"] = (
            f"Unsupported file type for '{filename}'. Please upload a valid PDF (.pdf) file."
        )
        return result

    # Read raw bytes safely
    try:
        if isinstance(file_obj, bytes):
            raw_bytes = file_obj
        elif hasattr(file_obj, "getvalue"):
            raw_bytes = file_obj.getvalue()
        elif hasattr(file_obj, "read"):
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            raw_bytes = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        else:
            with open(file_obj, "rb") as f:
                raw_bytes = f.read()
    except Exception as exc:
        result["error_message"] = f"Could not read file '{filename}': {str(exc)}"
        return result

    # Check for empty file (0 bytes)
    if not raw_bytes or len(raw_bytes) == 0:
        result["error_message"] = (
            f"The file '{filename}' is empty (0 bytes). Please upload a valid PDF containing text."
        )
        return result

    # Parse PDF using pypdf
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except PdfReadError:
        result["error_message"] = (
            f"The file '{filename}' is corrupted or not a valid PDF document."
        )
        return result
    except Exception as exc:
        result["error_message"] = (
            f"Failed to open PDF '{filename}': {str(exc)}"
        )
        return result

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            result["error_message"] = (
                f"The PDF '{filename}' is password-protected and cannot be read."
            )
            return result

    total_pages = len(reader.pages)
    result["page_count"] = total_pages

    if total_pages == 0:
        result["error_message"] = (
            f"The PDF '{filename}' has 0 pages. Please upload a PDF with readable text."
        )
        return result

    # FR-03: Extract text and retain page numbers for traceability
    page_segments: List[str] = []
    raw_content_parts: List[str] = []
    unreadable_pages: List[int] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            extracted = page.extract_text() or ""
            cleaned = extracted.strip()
        except Exception:
            cleaned = ""

        if cleaned:
            page_segments.append(f"--- [Page {idx}] ---\n{cleaned}")
            raw_content_parts.append(cleaned)
        else:
            unreadable_pages.append(idx)

    result["readable_pages"] = len(page_segments)
    result["unreadable_pages"] = unreadable_pages

    # FR-02: Reject scanned/image-only PDFs or PDFs with no readable text
    combined_raw_text = "\n\n".join(raw_content_parts).strip()
    if not combined_raw_text:
        result["error_message"] = (
            f"No readable text could be extracted from '{filename}'. "
            "It may be a scanned/image-only PDF or contain only blank pages. "
            "(Note: OCR may be added as a future enhancement for scanned PDFs.)"
        )
        return result

    full_labeled_text = "\n\n".join(page_segments)
    char_count = len(combined_raw_text)
    word_count = len(combined_raw_text.split())

    limitations: List[str] = []
    if unreadable_pages:
        pages_str = ", ".join(str(p) for p in unreadable_pages)
        limitations.append(
            f"{filename}: No extractable text on page(s) {pages_str} (possible image/blank pages)."
        )

    # Handle long documents gracefully (Section 12: Long document test case)
    if len(full_labeled_text) > max_chars:
        result["is_truncated"] = True
        full_labeled_text = (
            full_labeled_text[:max_chars]
            + "\n\n[... Document truncated at character limit to fit model context window ...]"
        )
        limitations.append(
            f"{filename}: Document length ({char_count:,} chars) exceeded the single-pass limit "
            f"({max_chars:,} chars) and was safely truncated to fit model input limits."
        )

    preview = combined_raw_text[:PREVIEW_CHAR_LIMIT]
    if len(combined_raw_text) > PREVIEW_CHAR_LIMIT:
        preview += "..."

    result["is_valid"] = True
    result["char_count"] = char_count
    result["word_count"] = word_count
    result["full_text"] = full_labeled_text
    result["preview_text"] = preview
    result["limitations_note"] = " ".join(limitations) if limitations else None

    return result
