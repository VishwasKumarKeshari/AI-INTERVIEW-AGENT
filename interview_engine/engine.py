from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from role_extractor import DetectedRole
from vector_store import InterviewVectorStore, QuestionRecord


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

        if len(self.roles) == 1:
            self.questions_per_role = {self.roles[0].name: 10}
        else:
            self.questions_per_role = {
                self.roles[0].name: 5,
                self.roles[1].name: 5,
            }

        self.role_order: List[str] = list(self.questions_per_role.keys())
        self.current_role_index: int = 0
        self.asked_question_ids: List[str] = []
        self.questions_by_role: Dict[str, List[QuestionWithEvaluation]] = {r: [] for r in self.role_order}

    def _current_role_name(self) -> str:
        return self.role_order[self.current_role_index]

    def has_more_questions(self) -> bool:
        for role_name, n_required in self.questions_per_role.items():
            if len(self.questions_by_role[role_name]) < n_required:
                return True
        return False

    def get_next_question(self) -> Optional[QuestionRecord]:
        """
        Retrieve the next question for the current role, switching roles once
        the quota for the current role is satisfied.
        """
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
        n_to_fetch = max(remaining, 1)
        fetched = self.store.get_questions_for_role(
            role=role_name,
            n=n_to_fetch,
            exclude_ids=self.asked_question_ids,
        )
        if not fetched:
            return None

        question = fetched[0]
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

