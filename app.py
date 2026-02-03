from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List

import streamlit as st

from resume_parser import parse_resume_file
from role_extractor import extract_roles_from_resume
from interview_engine import InterviewSession
from evaluation_engine import AnswerEvaluator
from report_generator import generate_report
from vector_store import InterviewVectorStore
from audio_io import transcribe_audio_file, speak_text


def _get_session() -> Dict[str, Any]:
    if "state" not in st.session_state:
        st.session_state.state = {}
    return st.session_state.state


def _init_interview(roles_text: str) -> None:
    state = _get_session()
    roles = state.get("roles", [])
    if not roles:
        st.error("No roles detected. Please upload and analyze a resume first.")
        return
    store = InterviewVectorStore()
    session = InterviewSession(roles=roles, store=store)
    state["interview_session"] = session
    state["evaluator"] = AnswerEvaluator()
    state["current_question"] = session.get_next_question()
    state["interview_completed"] = False


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
        roles = extract_roles_from_resume(cleaned)
        state["roles"] = roles
        st.success("Resume analyzed and roles extracted.")

    if "roles" in state:
        st.subheader("2. Detected Roles")
        for idx, r in enumerate(state["roles"], start=1):
            st.markdown(f"**Role {idx}: {r.name}** (confidence: {r.confidence:.2f})")
            st.caption(r.rationale)

    if "roles" in state and st.button("Start Interview"):
        _init_interview("roles")

    if "interview_session" in state:
        session: InterviewSession = state["interview_session"]
        evaluator: AnswerEvaluator = state["evaluator"]
        current_question = state.get("current_question")

        st.subheader("3. Interview")

        if current_question is None and not state.get("interview_completed", False):
            state["interview_completed"] = True

        if not state.get("interview_completed", False):
            st.markdown(f"**Current Role:** {current_question.role}")
            st.markdown(f"**Question:** {current_question.question}")

            st.write("You can answer by text or upload an audio response.")
            answer_text = st.text_area("Your answer (text)", key="answer_text_area")

            audio_file = st.file_uploader("Or upload an audio answer (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
            if st.button("Transcribe Audio") and audio_file is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio_file.read())
                    tmp_path = tmp.name
                transcript = transcribe_audio_file(tmp_path)
                os.remove(tmp_path)
                st.session_state["answer_text_area"] = transcript
                st.success("Audio transcribed into the text field above.")

            if st.button("Submit Answer"):
                final_answer = st.session_state.get("answer_text_area", "").strip()
                if not final_answer:
                    st.error("Please provide an answer before submitting.")
                else:
                    eval_result = evaluator.evaluate_answer(
                        role_name=current_question.role,
                        question=current_question.question,
                        ideal_answer=current_question.ideal_answer,
                        expected_concepts=current_question.expected_concepts,
                        candidate_answer=final_answer,
                    )
                    session.record_answer_evaluation(
                        question_id=current_question.id,
                        answer_text=final_answer,
                        score=int(eval_result["score"]),
                        reasoning=str(eval_result["reasoning"]),
                        strengths=list(eval_result["strengths"]),
                        weaknesses=list(eval_result["weaknesses"]),
                    )
                    st.success(f"Answer scored: {eval_result['score']} / 2")
                    with st.expander("Evaluation details"):
                        st.write(eval_result["reasoning"])
                        st.write("Strengths:", eval_result["strengths"])
                        st.write("Weaknesses:", eval_result["weaknesses"])

                    # Move to next question
                    if session.has_more_questions():
                        state["current_question"] = session.get_next_question()
                        st.session_state["answer_text_area"] = ""
                    else:
                        state["current_question"] = None
                        state["interview_completed"] = True

        if state.get("interview_completed", False):
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

