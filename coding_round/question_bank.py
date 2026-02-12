from __future__ import annotations

import io
import os
import re
from functools import lru_cache
from hashlib import md5
from typing import List

import pdfplumber
from docx import Document

from config import coding_round_config
from vector_store import QuestionRecord


_TITLE_PATTERN = re.compile(r"^\s*Question\s+(\d+)\s*[—-]\s*(.+?)\s*$", re.IGNORECASE)


def _extract_text(path: str) -> str:
    ext = os.path.splitext(path.lower())[1]
    if ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    if ext in {".doc", ".docx"}:
        with open(path, "rb") as f:
            doc = Document(io.BytesIO(f.read()))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_question_titles(text: str) -> List[str]:
    titles: List[str] = []
    for line in text.splitlines():
        match = _TITLE_PATTERN.match(line)
        if not match:
            continue
        title = _normalize_spaces(match.group(2))
        if title:
            titles.append(title)
    return titles


def _build_question_record(source_path: str, index: int, title: str) -> QuestionRecord:
    source_name = os.path.basename(source_path)
    qid_suffix = md5(f"{source_name}:{index}:{title}".encode("utf-8")).hexdigest()[:10]
    question_text = f"{title}. Write working code and explain time and space complexity."
    return QuestionRecord(
        id=f"coding_{qid_suffix}",
        question=question_text,
        role="coding_round",
        difficulty="medium",
        ideal_answer="Coding answer expected. No automatic scoring for coding round.",
        expected_concepts=["code correctness", "time complexity", "space complexity"],
    )


@lru_cache(maxsize=1)
def load_coding_round_questions() -> List[QuestionRecord]:
    questions: List[QuestionRecord] = []
    seen_titles: set[str] = set()

    for path in coding_round_config.question_files:
        if not os.path.exists(path):
            continue
        try:
            text = _extract_text(path)
        except Exception:
            continue

        for idx, title in enumerate(_extract_question_titles(text), start=1):
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            questions.append(_build_question_record(path, idx, title))

    return questions
