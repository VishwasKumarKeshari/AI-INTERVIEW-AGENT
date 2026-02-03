from __future__ import annotations

import io
import os
from typing import Tuple

import pdfplumber
from docx import Document


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    # python-docx expects a file-like object
    document = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _clean_text(text: str) -> str:
    cleaned = text.replace("\r", "\n")
    lines = [line.strip() for line in cleaned.splitlines()]
    non_empty = [line for line in lines if line]
    return "\n".join(non_empty)


def parse_resume_file(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    """
    Parse a resume file (PDF or DOCX) and return a tuple:
      (raw_text, cleaned_text)
    """
    _, ext = os.path.splitext(filename.lower())

    if ext == ".pdf":
        raw = _extract_text_from_pdf(file_bytes)
    elif ext in {".docx", ".doc"}:
        raw = _extract_text_from_docx(file_bytes)
    else:
        # Fallback: treat as plain text
        raw = file_bytes.decode("utf-8", errors="ignore")

    cleaned = _clean_text(raw)
    return raw, cleaned

