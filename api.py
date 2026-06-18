from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from audio_io import transcribe_audio_file
from evaluation_engine import AnswerEvaluator
from interview_engine import InterviewSession, QuestionWithEvaluation
from report_generator import generate_report
from resume_parser import parse_resume_file
from role_extractor import DetectedRole, extract_roles_from_resume
from vector_store import InterviewVectorStore, QuestionRecord


app = FastAPI(title="AI Interview Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class SessionState:
    session: InterviewSession
    evaluator: AnswerEvaluator
    created_at: float
    answer_log_path: Optional[str] = None
    evaluation_saved: bool = False


_SESSIONS: Dict[str, SessionState] = {}


class RoleInput(BaseModel):
    name: str
    confidence: float = 0.5
    rationale: str = ""


class StartInterviewRequest(BaseModel):
    resume_text: Optional[str] = None
    roles: Optional[List[RoleInput]] = None
    max_roles: int = 2


class StartInterviewResponse(BaseModel):
    session_id: str
    roles: List[RoleInput]
    total_questions: int


class QuestionResponse(BaseModel):
    id: str
    role: str
    question: str
    difficulty: str
    expected_concepts: List[str]


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(..., min_length=1)


class AnswerResponse(BaseModel):
    question_id: str
    has_more_questions: bool


def _get_session_state(session_id: str) -> SessionState:
    state = _SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")
    return state


def _question_to_response(question: QuestionRecord) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        role=question.role,
        question=question.question,
        difficulty=question.difficulty,
        expected_concepts=question.expected_concepts,
    )


def _find_question(session: InterviewSession, question_id: str) -> Optional[QuestionWithEvaluation]:
    for qlist in session.questions_by_role.values():
        for item in qlist:
            if item.question.id == question_id:
                return item
    return None


def _init_answer_log(state: SessionState) -> None:
    os.makedirs("interview_logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join("interview_logs", f"interview_answers_{timestamp}.json")
    roles = [r.name for r in state.session.roles]
    payload = {
        "started_at": datetime.now().isoformat(),
        "roles": roles,
        "answers": [],
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    state.answer_log_path = log_path


def _append_answer_log(
    state: SessionState,
    item: QuestionWithEvaluation,
    answer_text: str,
    was_timeout: bool,
) -> None:
    log_path = state.answer_log_path
    if not log_path:
        return
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        payload = {"started_at": datetime.now().isoformat(), "roles": [], "answers": []}

    payload["answers"].append(
        {
            "question_id": item.question.id,
            "role": item.question.role,
            "question": item.question.question,
            "answer_text": answer_text,
            "was_timeout": was_timeout,
            "answered_at": datetime.now().isoformat(),
        }
    )
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_evaluation_json(state: SessionState) -> None:
    if state.evaluation_saved:
        return
    log_path = state.answer_log_path
    if not log_path:
        return
    eval_path = log_path.replace("interview_answers_", "interview_evaluation_")
    data = state.session.to_serializable()
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    state.evaluation_saved = True


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/resume/parse")
async def parse_resume(file: UploadFile = File(...)) -> Dict[str, str]:
    file_bytes = await file.read()
    raw, cleaned = parse_resume_file(file.filename, file_bytes)
    return {"raw_text": raw, "cleaned_text": cleaned}


@app.post("/resume/analyze")
async def analyze_resume(file: UploadFile = File(...)) -> Dict[str, object]:
    file_bytes = await file.read()
    raw, cleaned = parse_resume_file(file.filename, file_bytes)
    roles = extract_roles_from_resume(cleaned)
    return {
        "raw_text": raw,
        "cleaned_text": cleaned,
        "roles": [RoleInput(name=r.name, confidence=r.confidence, rationale=r.rationale) for r in roles],
    }


@app.post("/roles/extract")
def extract_roles(payload: Dict[str, object]) -> Dict[str, object]:
    resume_text = str(payload.get("resume_text", "")).strip()
    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text is required.")
    max_roles = int(payload.get("max_roles", 2))
    roles = extract_roles_from_resume(resume_text, max_roles=max_roles)
    return {
        "roles": [RoleInput(name=r.name, confidence=r.confidence, rationale=r.rationale) for r in roles],
    }


@app.post("/interview/start", response_model=StartInterviewResponse)
def start_interview(payload: StartInterviewRequest) -> StartInterviewResponse:
    roles: List[DetectedRole] = []
    if payload.roles:
        roles = [DetectedRole(name=r.name, confidence=r.confidence, rationale=r.rationale) for r in payload.roles]
    elif payload.resume_text:
        roles = extract_roles_from_resume(payload.resume_text, max_roles=payload.max_roles)

    if not roles:
        raise HTTPException(status_code=400, detail="Provide roles or resume_text to start an interview.")

    store = InterviewVectorStore()
    store.seed_if_empty()
    session = InterviewSession(roles=roles, store=store)
    evaluator = AnswerEvaluator(store=store)

    session_id = str(uuid.uuid4())
    state = SessionState(session=session, evaluator=evaluator, created_at=time.time())
    _init_answer_log(state)
    _SESSIONS[session_id] = state

    total_questions = sum(session.questions_per_role.values()) + 1
    response_roles = [RoleInput(name=r.name, confidence=r.confidence, rationale=r.rationale) for r in roles]
    return StartInterviewResponse(session_id=session_id, roles=response_roles, total_questions=total_questions)


@app.get("/interview/{session_id}/question", response_model=Optional[QuestionResponse])
def get_next_question(session_id: str) -> Optional[QuestionResponse]:
    state = _get_session_state(session_id)
    question = state.session.get_next_question()
    if not question:
        return None
    return _question_to_response(question)


@app.post("/interview/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, payload: AnswerRequest) -> AnswerResponse:
    state = _get_session_state(session_id)
    item = _find_question(state.session, payload.question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found for this session.")

    if item.question.id == "warmup_1" or item.question.role == "coding_round":
        state.session.record_answer_evaluation(
            question_id=item.question.id,
            answer_text=payload.answer_text,
            score=None,
            reasoning=None,
            strengths=[],
            weaknesses=[],
        )
    else:
        eval_result = state.evaluator.evaluate_answer(
            question_id=item.question.id,
            role_name=item.question.role,
            question=item.question.question,
            ideal_answer=item.question.ideal_answer,
            expected_concepts=item.question.expected_concepts,
            candidate_answer=payload.answer_text,
        )
        state.session.record_answer_evaluation(
            question_id=item.question.id,
            answer_text=payload.answer_text,
            score=int(eval_result["score"]),
            reasoning=str(eval_result["reasoning"]),
            strengths=list(eval_result["strengths"]),
            weaknesses=list(eval_result["weaknesses"]),
        )
    _append_answer_log(
        state,
        item,
        payload.answer_text,
        was_timeout="(No answer - time expired)" in payload.answer_text,
    )

    return AnswerResponse(
        question_id=item.question.id,
        has_more_questions=state.session.has_more_questions(),
    )


@app.post("/interview/{session_id}/answer/audio", response_model=AnswerResponse)
async def submit_audio_answer(session_id: str, question_id: str, file: UploadFile = File(...)) -> AnswerResponse:
    state = _get_session_state(session_id)
    item = _find_question(state.session, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found for this session.")
    if item.question.role == "coding_round":
        raise HTTPException(
            status_code=400,
            detail="Coding round accepts text answers only. Use /interview/{session_id}/answer.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name
    try:
        answer_text = transcribe_audio_file(temp_path)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    if not answer_text:
        raise HTTPException(status_code=400, detail="Transcription returned empty text.")

    if item.question.id == "warmup_1" or item.question.role == "coding_round":
        state.session.record_answer_evaluation(
            question_id=item.question.id,
            answer_text=answer_text,
            score=None,
            reasoning=None,
            strengths=[],
            weaknesses=[],
        )
    else:
        eval_result = state.evaluator.evaluate_answer(
            question_id=item.question.id,
            role_name=item.question.role,
            question=item.question.question,
            ideal_answer=item.question.ideal_answer,
            expected_concepts=item.question.expected_concepts,
            candidate_answer=answer_text,
        )
        state.session.record_answer_evaluation(
            question_id=item.question.id,
            answer_text=answer_text,
            score=int(eval_result["score"]),
            reasoning=str(eval_result["reasoning"]),
            strengths=list(eval_result["strengths"]),
            weaknesses=list(eval_result["weaknesses"]),
        )
    _append_answer_log(
        state,
        item,
        answer_text,
        was_timeout=False,
    )

    return AnswerResponse(
        question_id=item.question.id,
        has_more_questions=state.session.has_more_questions(),
    )


@app.get("/interview/{session_id}/report")
def get_report(session_id: str) -> Dict[str, object]:
    state = _get_session_state(session_id)
    serializable = state.session.to_serializable()
    role_results = state.evaluator.aggregate_role_scores(serializable)
    final_summary = state.evaluator.generate_final_summary(serializable, role_results)
    _write_evaluation_json(state)
    return generate_report(serializable, role_results, final_summary=final_summary)


@app.get("/interview/{session_id}/export")
def export_interview(session_id: str) -> Dict[str, object]:
    state = _get_session_state(session_id)
    return state.session.to_serializable()


@app.delete("/interview/{session_id}")
def delete_session(session_id: str) -> Dict[str, str]:
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found.")


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


#python -m uvicorn api:app --reload --port 8000


# cd frontend
# python -m http.server 5500

# python -m vector_store.init_vector_store
