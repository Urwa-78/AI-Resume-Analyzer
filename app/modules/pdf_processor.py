"""
pdf_processor.py
----------------
Handles PDF upload validation and text extraction using PyMuPDF (fitz).
"""

from dataclasses import dataclass
from typing import Optional

import fitz  # PyMuPDF


class PDFProcessingError(Exception):
    """Raised when a PDF cannot be read or is invalid."""


@dataclass
class ExtractedPDF:
    text: str
    page_count: int
    file_name: str


def validate_pdf_bytes(file_bytes: bytes, file_name: str, max_size_mb: int = 10) -> None:
    """
    Validate a PDF before attempting extraction.
    Raises PDFProcessingError on any invalid condition.
    """
    if not file_bytes:
        raise PDFProcessingError("The uploaded file is empty.")

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise PDFProcessingError(
            f"File too large ({size_mb:.1f} MB). Maximum allowed is {max_size_mb} MB."
        )

    if not file_name.lower().endswith(".pdf"):
        raise PDFProcessingError("Only PDF files are supported.")

    # Basic magic-number check for a valid PDF header
    if not file_bytes[:5] == b"%PDF-":
        raise PDFProcessingError("The file does not appear to be a valid PDF.")


def extract_text_from_pdf(file_bytes: bytes, file_name: str = "resume.pdf") -> ExtractedPDF:
    """
    Extract full text content from a PDF file's bytes.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.
        file_name: Original file name (used for error messages/logging).

    Returns:
        ExtractedPDF dataclass with the concatenated text and metadata.

    Raises:
        PDFProcessingError: if the file is invalid, corrupted, or empty of text.
    """
    validate_pdf_bytes(file_bytes, file_name)

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # fitz raises generic exceptions on corrupt files
        raise PDFProcessingError(f"Could not open PDF: {exc}") from exc

    try:
        page_count = doc.page_count
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text("text"))
        full_text = "\n".join(text_parts).strip()
    finally:
        doc.close()

    if not full_text:
        raise PDFProcessingError(
            "No extractable text found in this PDF. It may be a scanned image "
            "without an OCR text layer."
        )

    return ExtractedPDF(text=full_text, page_count=page_count, file_name=file_name)


def extract_text_from_optional_source(
    uploaded_bytes: Optional[bytes], file_name: Optional[str], raw_text: Optional[str]
) -> str:
    """
    Convenience helper for the Job Description input, which can arrive either
    as an uploaded file (PDF/txt) or as pasted raw text.
    """
    if raw_text and raw_text.strip():
        return raw_text.strip()

    if uploaded_bytes:
        if file_name and file_name.lower().endswith(".pdf"):
            return extract_text_from_pdf(uploaded_bytes, file_name).text
        try:
            return uploaded_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            raise PDFProcessingError(f"Could not read job description file: {exc}") from exc

    raise PDFProcessingError("No job description text or file was provided.")
