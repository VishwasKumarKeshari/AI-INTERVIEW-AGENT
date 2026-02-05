from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_webrtc import webrtc_streamer

from resume_parser import parse_resume_file
from role_extractor import extract_roles_from_resume
from interview_engine import InterviewSession
from evaluation_engine import AnswerEvaluator
from report_generator import generate_report
from vector_store import InterviewVectorStore
from audio_io import transcribe_audio_file, speak_text, speak_text_async
from audio_io.realtime_vad import get_vad_state, create_audio_frame_callback


def _submit_answer_from_voice_or_auto(
    state: Dict[str, Any],
    session: InterviewSession,
    evaluator: AnswerEvaluator,
    current_question,
    answer_text: str,
) -> None:
    """Evaluate answer (from voice or auto-timeout) and advance to next question."""
    if "(No answer" in answer_text or not answer_text.strip():
        session.record_answer_evaluation(
            question_id=current_question.id,
            answer_text="(No answer - time expired)",
            score=0,
            reasoning="No answer provided within the time limit.",
            strengths=[],
            weaknesses=["No response submitted"],
        )
    else:
        eval_result = evaluator.evaluate_answer(
            role_name=current_question.role,
            question=current_question.question,
            ideal_answer=current_question.ideal_answer,
            expected_concepts=current_question.expected_concepts,
            candidate_answer=answer_text,
        )
        session.record_answer_evaluation(
            question_id=current_question.id,
            answer_text=answer_text,
            score=int(eval_result["score"]),
            reasoning=str(eval_result["reasoning"]),
            strengths=list(eval_result["strengths"]),
            weaknesses=list(eval_result["weaknesses"]),
        )
    if session.has_more_questions():
        state["current_question"] = session.get_next_question()
        get_vad_state().reset_for_new_question()
        state["question_started_at"] = time.time()
    else:
        state["current_question"] = None
        state["interview_completed"] = True
        state["question_started_at"] = None


def _init_answer_log(state: Dict[str, Any]) -> None:
    os.makedirs("interview_logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join("interview_logs", f"interview_answers_{timestamp}.json")
    roles = [r.name for r in state.get("roles", [])]
    payload = {
        "started_at": datetime.now().isoformat(),
        "roles": roles,
        "answers": [],
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    state["answer_log_path"] = log_path


def _append_answer_log(
    state: Dict[str, Any],
    current_question,
    answer_text: str,
    was_timeout: bool,
) -> None:
    log_path = state.get("answer_log_path")
    if not log_path:
        return
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        payload = {"started_at": datetime.now().isoformat(), "roles": [], "answers": []}

    payload["answers"].append(
        {
            "question_id": current_question.id,
            "role": current_question.role,
            "question": current_question.question,
            "answer_text": answer_text,
            "was_timeout": was_timeout,
            "answered_at": datetime.now().isoformat(),
        }
    )
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_evaluation_json(state: Dict[str, Any], session: InterviewSession) -> None:
    if state.get("evaluation_saved"):
        return
    log_path = state.get("answer_log_path")
    if not log_path:
        return
    eval_path = log_path.replace("interview_answers_", "interview_evaluation_")
    data = session.to_serializable()
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    state["evaluation_saved"] = True


def _get_session() -> Dict[str, Any]:
    if "state" not in st.session_state:
        st.session_state.state = {}
    return st.session_state.state


def _init_interview() -> None:
    state = _get_session()
    roles = state.get("roles", [])
    if not roles:
        st.error("No roles detected. Please upload and analyze a resume first.")
        return
    store = InterviewVectorStore()
    seeded = store.seed_if_empty()
    if seeded:
        st.info("Vector store was empty — seeded with sample questions.")
    session = InterviewSession(roles=roles, store=store)
    state["interview_session"] = session
    state["evaluator"] = AnswerEvaluator()
    state["interview_phase"] = "questions"
    state["current_question"] = session.get_next_question()
    state["interview_completed"] = False
    state["intro_spoken"] = False
    state["last_spoken_question_id"] = None
    state["outro_spoken"] = False
    _init_answer_log(state)
    get_vad_state().reset_for_new_question()
    state["question_started_at"] = time.time()


def _run_main_page() -> None:
    st.title("AI Interview Agent")

    state = _get_session()

    st.sidebar.header("Configuration")
    st.sidebar.write("This demo uses a local Whisper model and a vector store seeded with sample questions.")

    st.subheader("1. Upload Resume")
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx", "doc"])

    if uploaded_file is not None and st.button("Analyze Resume"):
        raw, cleaned = parse_resume_file(uploaded_file.name, uploaded_file.read())
        state["resume_raw"] = raw
        state["resume_cleaned"] = cleaned
        try:
            roles = extract_roles_from_resume(cleaned)
        except Exception as e:
            st.error("Role extraction failed. Check GROQ_API_KEY and LLM_MODEL in your environment/secrets.")
            st.exception(e)
            return
        state["roles"] = roles
        st.success("Resume analyzed and roles extracted.")

    if "roles" in state:
        st.subheader("2. Detected Roles")
        for idx, r in enumerate(state["roles"], start=1):
            st.markdown(f"**Role {idx}: {r.name}** (confidence: {r.confidence:.2f})")
            st.caption(r.rationale)

    if "roles" in state and "interview_session" not in state:
        _init_interview()

    if "interview_session" in state:
        session: InterviewSession = state["interview_session"]
        evaluator: AnswerEvaluator = state["evaluator"]
        phase = state.get("interview_phase", "intro")
        current_question = state.get("current_question")

        st.subheader("3. Interview")

        # --- Questions (warmup + technical) ---
        if phase == "questions" and not state.get("interview_completed", False):
            vad = get_vad_state()
            if state.get("question_started_at") is None:
                state["question_started_at"] = time.time()
            elapsed_sec = time.time() - float(state.get("question_started_at") or time.time())
            # Voice-based: 60s answer window (hard timer)
            if elapsed_sec >= 60:
                triggered = True
                audio_path = vad.finalize_audio_path()
            else:
                triggered, audio_path = vad.pop_triggered_and_audio_path()
            if triggered and current_question:
                transcript = ""
                if audio_path:
                    try:
                        transcript = transcribe_audio_file(audio_path).strip()
                        os.remove(audio_path)
                    except Exception:
                        pass
                _append_answer_log(
                    state,
                    current_question,
                    transcript if transcript else "(No answer - time expired)",
                    was_timeout=not bool(transcript),
                )
                _submit_answer_from_voice_or_auto(
                    state, session, evaluator, current_question,
                    transcript if transcript else "(No answer - time expired)",
                )
                st.rerun()

            if state.get("interview_completed", False):
                pass  # Fall through to results
            elif current_question:
                st.caption(
                    f"Debug | qid: {current_question.id} | elapsed: {elapsed_sec:.1f}s | "
                    f"triggered: {triggered} | asked: {len(session.asked_question_ids)}"
                )
                if not state.get("intro_spoken"):
                    role_names = ", ".join(r.name for r in session.roles)
                    intro_msg = (
                        f"Hello! I'm your AI Interview Agent. "
                        f"I'll be conducting your technical interview today for the role(s): {role_names}. "
                        f"We'll start with a quick introduction, then move on to technical questions. "
                        f"Speak into your mic—your answer window is 60 seconds. "
                        f"Let's begin!"
                    )
                    state["intro_spoken"] = True
                    speak_text_async(intro_msg)
                    st.info(
                        f"**Hello! I'm your AI Interview Agent.**\n\n"
                        f"I'll be conducting your technical interview today for the role(s): **{role_names}**.\n\n"
                        f"We'll start with a quick introduction, then move on to {9 if len(session.roles) == 1 else 9} technical questions. "
                        f"**Speak into your mic**—you have **60 seconds** for each answer.\n\n"
                        f"Let's begin!"
                    )
                # Speak the question aloud when first shown (once per question)
                last_spoken = state.get("last_spoken_question_id")
                if last_spoken != current_question.id:
                    state["last_spoken_question_id"] = current_question.id
                    speak_text_async(current_question.question)

                st.markdown(f"**Role:** {current_question.role}")
                st.markdown(f"**Question:** {current_question.question}")

                elapsed_sec = time.time() - float(state.get("question_started_at") or time.time())
                remaining = max(0, 60 - int(elapsed_sec))
                rms_level = vad.get_last_rms()
                if vad.is_speaking():
                    st.caption(f"Speaking... (You have up to 60 seconds total) | RMS: {rms_level:.4f}")
                else:
                    st.caption(f"Time remaining: {remaining}s / 60s | RMS: {rms_level:.4f}")

                st.markdown("**Answer by voice (real-time)** — speak into your mic. You have 60 seconds per question.")
                webrtc_streamer(
                    key="interview_mic",
                    audio_frame_callback=create_audio_frame_callback(),
                    media_stream_constraints={"video": False, "audio": True},
                )

                # Poll every 1s to check if VAD reached the 60s limit
                st_autorefresh(interval=1000, key="question_timer")
            else:
                if session.has_more_questions():
                    st.error(
                        "No more questions available in the vector store. "
                        "Please seed the vector store with more questions."
                    )
                    st.stop()
                state["interview_completed"] = True
                st.rerun()

        # --- Results ---
        if state.get("interview_completed", False):
            if not state.get("outro_spoken"):
                state["outro_spoken"] = True
                speak_text_async("Thank you for your time. The interview is now complete.")
            _write_evaluation_json(state, session)
            st.subheader("4. Results")
            interview_state = session.to_serializable()
            evaluator: AnswerEvaluator = state["evaluator"]
            role_results = evaluator.aggregate_role_scores(interview_state)
            report = generate_report(interview_state, role_results)

            for role_report in report["roles"]:
                st.markdown(f"### {role_report['role_name']}")
                st.write(f"Score: **{role_report['score_out_of_10']} / 10**")
                st.caption(f"Role rationale: {role_report['role_rationale']}")

                st.markdown("**Strengths**")
                for s in role_report["strengths"]:
                    st.write(f"- {s}")

                st.markdown("**Weaknesses**")
                for w in role_report["weaknesses"]:
                    st.write(f"- {w}")

            st.info(f"Total questions asked: {report['total_questions']}")


def main() -> None:
    _run_main_page()


if __name__ == "__main__":
    main()

