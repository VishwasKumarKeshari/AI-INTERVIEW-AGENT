from __future__ import annotations

import os
import tempfile
import time
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
        st.session_state["answer_text_area"] = ""
    else:
        state["current_question"] = None
        state["interview_completed"] = True


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
    session = InterviewSession(roles=roles, store=store)
    state["interview_session"] = session
    state["evaluator"] = AnswerEvaluator()
    state["interview_phase"] = "intro"  # intro -> warmup -> technical
    state["current_question"] = None
    state["interview_completed"] = False
    state["intro_spoken"] = False
    state["last_spoken_question_id"] = None


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

    if "roles" in state and st.button("Start Interview"):
        _init_interview()

    if "interview_session" in state:
        session: InterviewSession = state["interview_session"]
        evaluator: AnswerEvaluator = state["evaluator"]
        phase = state.get("interview_phase", "intro")
        current_question = state.get("current_question")

        st.subheader("3. Interview")

        # --- Phase 1: Introduction ---
        if phase == "intro":
            role_names = ", ".join(r.name for r in session.roles)
            intro_msg = (
                f"Hello! I'm your AI Interview Agent. "
                f"I'll be conducting your technical interview today for the role(s): {role_names}. "
                f"We'll start with a quick introduction, then move on to technical questions. "
                f"Speak into your mic—the 10-second timer starts only when you stop talking. "
                f"Let's begin!"
            )
            if not state.get("intro_spoken"):
                state["intro_spoken"] = True
                speak_text_async(intro_msg)
            st.info(
                f"**Hello! I'm your AI Interview Agent.**\n\n"
                f"I'll be conducting your technical interview today for the role(s): **{role_names}**.\n\n"
                f"We'll start with a quick introduction, then move on to {9 if len(session.roles) == 1 else 9} technical questions. "
                f"**Speak into your mic**—the 10-second timer starts only **when you stop talking**. You can also type your answer.\n\n"
                f"Let's begin!"
            )
            if st.button("Let's begin"):
                state["interview_phase"] = "questions"
                state["current_question"] = session.get_next_question()
                vad = get_vad_state()
                vad.reset_for_new_question()
                st.rerun()

        # --- Phase 2 & 3: Questions (warmup + technical) ---
        elif phase == "questions" and not state.get("interview_completed", False):
            vad = get_vad_state()
            # VAD-based: 10 sec timer starts only when candidate STOPS speaking
            triggered, audio_path = vad.pop_triggered_and_audio_path()
            if triggered and current_question:
                transcript = ""
                if audio_path:
                    try:
                        transcript = transcribe_audio_file(audio_path).strip()
                        os.remove(audio_path)
                    except Exception:
                        pass
                _submit_answer_from_voice_or_auto(
                    state, session, evaluator, current_question,
                    transcript if transcript else "(No answer - time expired)",
                )
                st.rerun()

            if state.get("interview_completed", False):
                pass  # Fall through to results
            elif current_question:
                # Speak the question aloud when first shown (once per question)
                last_spoken = state.get("last_spoken_question_id")
                if last_spoken != current_question.id:
                    state["last_spoken_question_id"] = current_question.id
                    speak_text_async(current_question.question)

                st.markdown(f"**Role:** {current_question.role}")
                st.markdown(f"**Question:** {current_question.question}")

                silence_sec = vad.get_silence_seconds()
                if vad.is_speaking() or silence_sec < 0.5:
                    st.caption("🎤 **Speaking...** (Timer starts when you stop talking)")
                else:
                    st.caption(f"⏱️ **Silence:** {int(silence_sec)}s / 10s (auto-advances when you stay silent 10 sec)")

                st.markdown("**Answer by voice (real-time)** — speak into your mic. The 10s timer starts only when you stop.")
                webrtc_streamer(
                    key=f"interview_mic_{current_question.id}",
                    audio_frame_callback=create_audio_frame_callback(),
                    media_stream_constraints={"video": False, "audio": True},
                )

                st.markdown("**Or type your answer:**")
                answer_text = st.text_area("Your answer (text)", key="answer_text_area")

                audio_file = st.file_uploader("Or upload an audio file (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
                if st.button("Transcribe Audio File") and audio_file is not None:
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
                        _submit_answer_from_voice_or_auto(
                            state, session, evaluator, current_question, final_answer
                        )
                        st.success("Answer submitted and scored.")
                        st.rerun()

                # Poll every 1.5s to check if VAD detected 10s silence
                st_autorefresh(interval=1500, key="question_timer")
            else:
                state["interview_completed"] = True
                st.rerun()

        # --- Results ---
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

