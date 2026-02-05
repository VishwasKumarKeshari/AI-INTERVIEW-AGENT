from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from role_extractor import DetectedRole
from vector_store import InterviewVectorStore, QuestionRecord
from llm_client import llm_client
from prompts import QUESTION_SELECTION_SYSTEM_PROMPT


@dataclass
class QuestionWithEvaluation:
    question: QuestionRecord
    answer_text: Optional[str] = None
    score: Optional[int] = None
    reasoning: Optional[str] = None
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


class InterviewSession:
    """
    Maintains the interview flow:
    - Allocates exactly 10 questions overall.
    - If 1 role: 10 questions; if 2 roles: 5 each.
    - Uses the vector store to fetch questions, avoiding duplicates.
    """

    def __init__(self, roles: List[DetectedRole], store: Optional[InterviewVectorStore] = None) -> None:
        if not roles:
            raise ValueError("At least one role is required to start an interview.")

        self.roles = roles[:2]
        self.store = store or InterviewVectorStore()

        # 1 warmup + 9 technical = 10 total. For 2 roles: 1 warmup + 4+5 technical.
        if len(self.roles) == 1:
            self.questions_per_role = {self.roles[0].name: 9}
        else:
            self.questions_per_role = {
                self.roles[0].name: 4,
                self.roles[1].name: 5,
            }

        self.role_order: List[str] = list(self.questions_per_role.keys())
        self.current_role_index: int = 0
        self.asked_question_ids: List[str] = []
        self.questions_by_role: Dict[str, List[QuestionWithEvaluation]] = {r: [] for r in self.role_order}
        self.warmup_done: bool = False
        self._warmup_record: QuestionRecord = QuestionRecord(
            id="warmup_1",
            question="Tell me about yourself. What interests you about this role?",
            role=self.role_order[0],
            difficulty="easy",
            ideal_answer="A strong answer covers background, relevant experience, motivation for the role, and key strengths. Clear communication and enthusiasm are valued.",
            expected_concepts=["self-introduction", "motivation", "background", "experience"],
        )

    def _current_role_name(self) -> str:
        return self.role_order[self.current_role_index]

    def _select_question_with_llm(
        self,
        role_name: str,
        candidates: List[QuestionRecord],
    ) -> QuestionRecord:
        if not candidates:
            raise ValueError("No candidate questions provided for selection.")
        if len(candidates) == 1:
            return candidates[0]

        user_payload = {
            "role": role_name,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "difficulty": q.difficulty,
                    "expected_concepts": q.expected_concepts,
                }
                for q in candidates
            ],
        }
        response = llm_client.chat(
            system_prompt=QUESTION_SELECTION_SYSTEM_PROMPT,
            user_prompt=json.dumps(user_payload, indent=2),
            max_tokens=128,
        )
        try:
            data = json.loads(response)
            selected_id = str(data.get("selected_id", ""))
        except json.JSONDecodeError:
            selected_id = ""

        by_id = {q.id: q for q in candidates}
        return by_id.get(selected_id, candidates[0])

    def has_more_questions(self) -> bool:
        for role_name, n_required in self.questions_per_role.items():
            if len(self.questions_by_role[role_name]) < n_required:
                return True
        return False

    def get_next_question(self) -> Optional[QuestionRecord]:
        """
        Retrieve the next question: first returns warmup, then technical questions
        from the vector store for the current role.
        """
        # First question is always the warmup.
        if not self.warmup_done:
            self.warmup_done = True
            self.questions_by_role[self.role_order[0]].append(
                QuestionWithEvaluation(question=self._warmup_record)
            )
            return self._warmup_record

        if not self.has_more_questions():
            return None

        role_name = self._current_role_name()
        quota = self.questions_per_role[role_name]
        current_count = len(self.questions_by_role[role_name])

        if current_count >= quota:
            # Move to next role that still has remaining questions
            for idx, rname in enumerate(self.role_order):
                if len(self.questions_by_role[rname]) < self.questions_per_role[rname]:
                    self.current_role_index = idx
                    role_name = rname
                    quota = self.questions_per_role[rname]
                    break

        if len(self.questions_by_role[role_name]) >= quota:
            return None

        remaining = quota - len(self.questions_by_role[role_name])
        n_to_fetch = min(5, max(remaining, 1) + 2)
        fetched = self.store.get_questions_for_role(
            role=role_name,
            n=n_to_fetch,
            exclude_ids=self.asked_question_ids,
        )
        if not fetched:
            # Fallback: allow repeats if the pool is exhausted.
            fetched = self.store.get_questions_for_role(
                role=role_name,
                n=1,
                exclude_ids=None,
            )
            if not fetched:
                return None

        question = self._select_question_with_llm(role_name, fetched)
        self.asked_question_ids.append(question.id)
        self.questions_by_role[role_name].append(QuestionWithEvaluation(question=question))
        return question

    def record_answer_evaluation(
        self,
        question_id: str,
        answer_text: str,
        score: int,
        reasoning: str,
        strengths: List[str],
        weaknesses: List[str],
    ) -> None:
        """
        Store evaluation results for a given question.
        """
        for role_name, qlist in self.questions_by_role.items():
            for item in qlist:
                if item.question.id == question_id:
                    item.answer_text = answer_text
                    item.score = score
                    item.reasoning = reasoning
                    item.strengths = strengths
                    item.weaknesses = weaknesses
                    return

    def to_serializable(self) -> Dict[str, Dict[str, List[Dict[str, object]]]]:
        """
        Convert internal state to a JSON-serializable structure for persistence.
        """
        data: Dict[str, Dict[str, List[Dict[str, object]]]] = {"roles": {}, "questions": {}}
        data["roles"] = {
            role.name: {
                "confidence": role.confidence,
                "rationale": role.rationale,
            }
            for role in self.roles
        }
        for role_name, qlist in self.questions_by_role.items():
            data["questions"][role_name] = []
            for item in qlist:
                data["questions"][role_name].append(
                    {
                        "id": item.question.id,
                        "question": item.question.question,
                        "difficulty": item.question.difficulty,
                        "ideal_answer": item.question.ideal_answer,
                        "expected_concepts": item.question.expected_concepts,
                        "answer_text": item.answer_text,
                        "score": item.score,
                        "reasoning": item.reasoning,
                        "strengths": item.strengths,
                        "weaknesses": item.weaknesses,
                    }
                )
        return data

