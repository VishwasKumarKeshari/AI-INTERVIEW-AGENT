from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from llm_client import llm_client
from prompts import ANSWER_EVAL_SYSTEM_PROMPT


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

    def evaluate_answer(
        self,
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
            return {
                "score": 1,
                "reasoning": "Default partial score due to parsing error.",
                "strengths": [],
                "weaknesses": [],
            }

        score = int(data.get("score", 1))
        if score not in {0, 1, 2}:
            score = 1

        return {
            "score": score,
            "reasoning": str(data.get("reasoning", "")),
            "strengths": list(data.get("strengths", [])),
            "weaknesses": list(data.get("weaknesses", [])),
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
            max_possible = len(scores) * 2
            normalized = (total / max_possible) * 10.0 if max_possible > 0 else 0.0
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

