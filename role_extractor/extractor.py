from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from llm_client import llm_client
from prompts import ROLE_EXTRACTION_SYSTEM_PROMPT


@dataclass
class DetectedRole:
    name: str
    confidence: float
    rationale: str


def extract_roles_from_resume(resume_text: str, max_roles: int = 2) -> List[DetectedRole]:
    """
    Use an LLM to infer up to `max_roles` suitable technical roles from the resume text.
    """
    user_prompt = f"RESUME TEXT:\n\"\"\"\n{resume_text}\n\"\"\"\n\nReturn JSON only."
    response = llm_client.chat(
        system_prompt=ROLE_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=512,
    )

    try:
        # Some models may wrap JSON with extra text; try to extract the JSON object.
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(response[start : end + 1])
        else:
            data = json.loads(response)
    except json.JSONDecodeError:
        # Fallback: treat the whole response as a single low-confidence generic role
        return [DetectedRole(name="General Technical Candidate", confidence=0.5, rationale="Fallback role due to parsing error.")]

    roles_data = data.get("roles", [])
    roles: List[DetectedRole] = []
    for r in roles_data[:max_roles]:
        name = str(r.get("name", "General Technical Candidate"))
        confidence = float(r.get("confidence", 0.5))
        rationale = str(r.get("rationale", ""))
        roles.append(DetectedRole(name=name, confidence=confidence, rationale=rationale))

    if not roles:
        roles.append(
            DetectedRole(
                name="General Technical Candidate",
                confidence=0.5,
                rationale="Default role when no roles were returned.",
            )
        )

    return roles

