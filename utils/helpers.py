"""
helpers.py
----------
Small, reusable utility functions shared across modules:
text cleaning, validation, and formatting helpers.
"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Normalize whitespace, remove weird unicode artifacts, and lowercase-safe
    the text for downstream NLP processing while preserving original
    line breaks for section-based parsing.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    # Collapse excessive blank lines but keep paragraph structure
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_matching(text: str) -> str:
    """Lowercase and strip punctuation for keyword/skill matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\+\#\.\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$", value))


def is_non_empty(text: str) -> bool:
    return bool(text and text.strip())


def truncate(text: str, max_chars: int = 6000) -> str:
    """Truncate long text (e.g. before sending to an LLM) with a marker."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]..."


def format_percentage(value: float) -> str:
    return f"{round(value)}%"


def safe_filename(name: str) -> str:
    """Strip unsafe characters from an uploaded file name before saving."""
    name = re.sub(r"[^\w\.\-]", "_", name)
    return name[:150]
