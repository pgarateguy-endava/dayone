"""Endava Profile PDF ingestion. (Read tool helper)"""
from __future__ import annotations

import io

MAX_CHARS = 8000  # keep the agent context bounded


def extract_pdf_text(data: bytes) -> str:
    """Extract plain text from a PDF (Endava Profile). Returns '' on failure."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return " ".join(text.split())[:MAX_CHARS]
    except Exception:
        return ""
