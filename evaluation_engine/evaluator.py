from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from llm_client import llm_client
from prompts import ANSWER_EVAL_SYSTEM_PROMPT, FINAL_SUMMARY_SYSTEM_PROMPT


@dataclass
class RoleEvaluationResult:
    role_name: str
    per_question_scores: List[int]
    total_score: float
    max_possible: int
    normalized_score: float
    strengths: List[str]
    weaknesses: List[str]


class AnswerEvaluator:
    """
    Uses the LLM to evaluate each answer and aggregates scores per role.
    """

    def __init__(self, store: Optional[Any] = None) -> None:
        self._store = store

    @staticmethod
    def _safe_llm_score(value: object, default: int = 1) -> int:
        try:
            score = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
        return max(0, min(2, score))

    def evaluate_answer(
        self,
        question_id: str,
        role_name: str,
        question: str,
        ideal_answer: str,
        expected_concepts: List[str],
        candidate_answer: str,
    ) -> Dict[str, object]:
        user_prompt = json.dumps(
            {
                "role": role_name,
                "question": question,
                "ideal_answer": ideal_answer,
                "expected_concepts": expected_concepts,
                "candidate_answer": candidate_answer,
            },
            indent=2,
        )
        response = llm_client.chat(
            system_prompt=ANSWER_EVAL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=512,
        )
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = {
                "score": 1,
                "reasoning": "Default partial score due to parsing error.",
                "strengths": [],
                "weaknesses": [],
            }

        semantic = None
        if self._store is not None and candidate_answer.strip():
            try:
                semantic = self._store.semantic_answer_score(
                    question_id=question_id,
                    candidate_answer=candidate_answer,
                )
            except Exception:
                semantic = None

        similarity = float(semantic["similarity"]) if semantic else 0.0
        llm_score_0_2 = self._safe_llm_score(data.get("score"), default=1)
        semantic_score_0_2 = float(semantic["score"]) if semantic and "score" in semantic else float(llm_score_0_2)

        # Blend rubric score (LLM) with embedding semantic score, then scale to 0-100.
        blended_0_2 = (0.7 * float(llm_score_0_2)) + (0.3 * semantic_score_0_2)
        score = int(round((blended_0_2 / 2.0) * 100.0))

        raw_strengths = data.get("strengths", [])
        raw_weaknesses = data.get("weaknesses", [])
        strengths = [str(s) for s in raw_strengths] if isinstance(raw_strengths, list) else []
        weaknesses = [str(w) for w in raw_weaknesses] if isinstance(raw_weaknesses, list) else []

        return {
            "score": score,
            "reasoning": str(data.get("reasoning", "")),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "semantic_similarity": similarity,
            "semantic_score": semantic_score_0_2,
            "llm_score": llm_score_0_2,
            "blended_score_0_2": round(blended_0_2, 3),
        }

    def aggregate_role_scores(
        self,
        interview_state: Dict[str, Dict[str, List[Dict[str, object]]]],
    ) -> List[RoleEvaluationResult]:
        """
        Compute final role-wise scores out of 10 based on per-question scores.
        """
        results: List[RoleEvaluationResult] = []
        questions_by_role = interview_state.get("questions", {})
        for role_name, qlist in questions_by_role.items():
            scores: List[int] = []
            strengths: List[str] = []
            weaknesses: List[str] = []
            for q in qlist:
                if q.get("score") is not None:
                    scores.append(int(q["score"]))  # type: ignore[index]
                strengths.extend(list(q.get("strengths", [])))
                weaknesses.extend(list(q.get("weaknesses", [])))
            if not scores:
                continue
            total = sum(scores)
            max_possible = len(scores) * 100
            normalized = (total / max_possible) * 100.0 if max_possible > 0 else 0.0
            results.append(
                RoleEvaluationResult(
                    role_name=role_name,
                    per_question_scores=scores,
                    total_score=float(total),
                    max_possible=max_possible,
                    normalized_score=normalized,
                    strengths=strengths,
                    weaknesses=weaknesses,
                )
            )
        return results

    def generate_final_summary(
        self,
        interview_state: Dict[str, Dict[str, List[Dict[str, object]]]],
        role_results: List[RoleEvaluationResult],
    ) -> str:
        """
        Generate a concise final summary using the LLM.
        """
        try:
            payload = {
                "roles": [
                    {
                        "role_name": r.role_name,
                        "score_percent": round(r.normalized_score, 2),
                    }
                    for r in role_results
                ],
                "questions": interview_state.get("questions", {}),
            }
            response = llm_client.chat(
                system_prompt=FINAL_SUMMARY_SYSTEM_PROMPT,
                user_prompt=json.dumps(payload, indent=2),
                max_tokens=256,
            )
            return response.strip()
        except Exception:
            return "Summary unavailable."

