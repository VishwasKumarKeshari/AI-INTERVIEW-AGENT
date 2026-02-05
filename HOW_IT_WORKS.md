## How It Works

This document gives a brief, implementation-level overview of how each part of the project fits together.

### Top-Level Flow

1. **User uploads resume** in `app.py`.
2. **`resume_parser/`** converts the file to clean text.
3. **`role_extractor/`** calls the LLM to detect up to 2 roles.
4. **`interview_engine/` + `vector_store/`**:
   - Decide how many questions per role (10 total).
   - Retrieve role-specific questions from the Chroma vector DB.
5. For each question:
   - User answers (text or audio → Whisper).
   - **`evaluation_engine/`** calls the LLM to score the answer (0–2) and returns reasoning.
   - **`interview_engine/`** stores the evaluation result in its in-memory state.
6. After 10 questions:
   - **`evaluation_engine/`** aggregates per-role scores.
   - **`report_generator/`** builds a final role-wise report.
   - **`app.py`** renders the results in Streamlit.

---

### Folder-by-Folder Overview

#### `resume_parser/`

- **Goal**: Turn uploaded resumes into clean text for analysis.
- **Key file**: `parser.py`
  - Detects file type (PDF, DOCX, or other).
  - Uses `pdfplumber` for PDFs and `python-docx` for DOCX.
  - Normalizes whitespace and line breaks.
  - Returns `(raw_text, cleaned_text)` to the Streamlit app.

#### `role_extractor/`

- **Goal**: Infer up to 2 suitable technical roles from the resume text.
- **Key files**:
  - `extractor.py`:
    - Defines `DetectedRole` (name, confidence, rationale).
    - Builds a structured prompt and calls the shared `llm_client`.
    - Robustly parses LLM JSON output, with fallback to a generic role if parsing fails.
  - `prompts/role_extraction_prompt.py`:
    - System prompt that:
      - Explains how to interpret the resume.
      - Restricts role names to a fixed list aligned with the vector DB (e.g., Backend Engineer, Data Scientist, ML Engineer).
      - Enforces a strict JSON response format.

#### `vector_store/`

- **Goal**: Provide a RAG-compatible store of interview questions.
- **Key files**:
  - `store.py`:
    - Wraps **Chroma** as a persistent vector DB (`vector_store/chroma_db/`).
    - Uses **Sentence Transformers** for embeddings.
    - Stores each question as:
      - Document: `question`
      - Metadata: `role`, `difficulty`, `ideal_answer`, `expected_concepts` (JSON string)
    - Exposes `get_questions_for_role(role, n, exclude_ids)`:
      - Embeds a query like `"Technical interview question for role: Backend Engineer"`.
      - Filters by `role` and excludes already asked IDs.
  - `init_vector_store.py`:
    - Script you run once to seed the DB:
      - `python -m vector_store.init_vector_store`
    - Builds a small but realistic set of question records and adds them to Chroma.

#### `interview_engine/`

- **Goal**: Orchestrate the interview (question allocation and state).
- **Key file**: `engine.py`
  - `QuestionWithEvaluation`:
    - Holds the question plus:
      - `answer_text`, `score`, `reasoning`, `strengths`, `weaknesses`.
  - `InterviewSession`:
    - Accepts detected roles and a `InterviewVectorStore`.
    - Enforces the rules:
      - 1 role → 10 questions.
      - 2 roles → 5 questions each.
      - Exactly 10 questions total, no repeats.
    - Keeps track of:
      - Which questions have been asked per role.
      - Current role index and list of asked question IDs.
    - Provides:
      - `get_next_question()` to select the next role-specific question from the vector DB.
      - `record_answer_evaluation(...)` to attach scores and feedback to each question.
      - `to_serializable()` to export all interview data for reporting.

#### `evaluation_engine/`

- **Goal**: Evaluate individual answers and compute final role-wise scores.
- **Key file**: `evaluator.py`
  - `AnswerEvaluator`:
    - `evaluate_answer(...)`:
      - Packages role, question, ideal answer, expected concepts, and candidate answer into JSON.
      - Sends it to the LLM (via `llm_client` and `prompts/evaluation_prompt.py`).
      - Parses a strict JSON response with:
        - `score` (0–2)
        - `reasoning`
        - `strengths`, `weaknesses`
      - Includes a safe fallback if JSON parsing fails.
    - `aggregate_role_scores(interview_state)`:
      - Reads all per-question scores from the serialized `InterviewSession`.
      - For each role:
        - Computes `total_score` and `max_possible` (questions × 2).
        - Calculates `normalized_score` out of 10.
        - Aggregates strengths and weaknesses into role-level lists.
  - `prompts/evaluation_prompt.py`:
    - System prompt that defines the scoring rubric (0, 1, 2) and output JSON shape.

#### `report_generator/`

- **Goal**: Turn raw scores and feedback into a user-friendly report.
- **Key file**: `generator.py`
  - `generate_report(interview_state, role_results)`:
    - Combines:
      - Role detection metadata (name, confidence, rationale).
      - Role-wise scores and feedback from `RoleEvaluationResult`.
    - Produces a final dict with:
      - Each role’s score out of 10.
      - Total raw score and max possible.
      - Short, deduplicated lists of strengths and weaknesses.
      - Total number of questions asked across roles.

#### `audio_io/`

- **Goal**: Handle audio input and (optional) speech output.
- **Key files**:
  - `stt.py`:
    - Loads a local Whisper model (configurable via `WHISPER_MODEL`).
    - Exposes `transcribe_audio_file(path)` to turn audio answers into text.
  - `tts.py`:
    - Wraps `pyttsx3` with lazy initialization:
      - Works locally where audio output is available.
      - Gracefully degrades to a no-op on platforms without audio (e.g., Streamlit Cloud).
    - Exposes `speak_text(text)` for text-to-speech.

#### `llm_client/`

- **Goal**: Centralized Groq LLM integration.
- **Key file**: `client.py`
  - `LLMClient`:
    - Uses the **Groq** Python SDK only.
    - Reads `LLM_MODEL` and `GROQ_API_KEY` from the environment.
    - Provides `chat(system_prompt, user_prompt, max_tokens)`:
      - Encapsulates the OpenAI-compatible `chat.completions.create` call.
  - Shared instance `llm_client` is imported wherever LLM calls are needed.

#### `prompts/`

- **Goal**: Keep prompt templates separate and reusable.
- **Files**:
  - `role_extraction_prompt.py`:
    - Prompt for mapping resume text → up to two roles from a fixed list.
  - `evaluation_prompt.py`:
    - Prompt for scoring answers (0–2) and generating structured feedback.

#### `config.py`

- **Goal**: Central configuration for LLMs, embeddings, vector store, and audio.
- Uses `python-dotenv` to load `.env` and exposes:
  - `llm_config` – Groq provider, model, temperature.
  - `embedding_config` – Sentence Transformers model name.
  - `vector_store_config` – Chroma path and collection name.
  - `audio_config` – Whisper model name.

#### `app.py`

- **Goal**: Streamlit frontend and orchestration glue.
- Handles:
  - Resume upload and parsing.
  - Role extraction display.
  - Interview start and per-question loop.
  - Audio upload and transcription.
  - Calling evaluation engine for each answer.
  - Calling report generator at the end and rendering the final results.

---

### State and Persistence Summary

- **Persistent DB**:
  - Chroma at `vector_store/chroma_db/` for interview questions (RAG).
- **In-memory state**:
  - `InterviewSession` and all scores are stored in `st.session_state` for the active user session.
  - When the session ends, those evaluations are not saved to disk (ready for future extension to a database if needed).

