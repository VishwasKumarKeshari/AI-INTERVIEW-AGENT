## AI Interview Agent

An end-to-end, modular AI-powered technical interview agent built with Python and Streamlit.
It parses a candidate's resume, detects up to two suitable technical roles, conducts a structured
interview with exactly 10 questions, evaluates answers using RAG + LLMs, and produces role-wise
scores out of 10 with strengths and weaknesses.

### Architecture Overview

- **`resume_parser/`**: Loads a resume (PDF or DOCX) and converts it into clean text.
- **`role_extractor/`**: Uses an LLM to infer up to 2 suitable technical roles from the resume text.
- **`vector_store/`**:
  - Wraps Chroma with Sentence Transformers embeddings.
  - Stores curated interview questions with metadata:
    - `question`
    - `role`
    - `difficulty`
    - `ideal_answer`
    - `expected_concepts`
  - Supports metadata filtering by `role` and similarity search.
- **`interview_engine/`**:
  - `InterviewSession` enforces the interview rules:
    - Exactly 10 questions total.
    - If 1 role → 10 questions.
    - If 2 roles → 5 questions per role.
    - No question is repeated.
    - All questions come from the vector DB.
  - Maintains interview state and role-wise question allocation.
- **`evaluation_engine/`**:
  - `AnswerEvaluator` uses an LLM to score each answer from 0–2.
  - Aggregates per-role scores and computes normalized role scores out of 10.
- **`report_generator/`**:
  - Builds the final role-wise report:
    - Role name and detection rationale.
    - Role score out of 10.
    - Summarized strengths and weaknesses.
- **`audio_io/`**:
  - `stt.py`: Whisper-based speech-to-text for audio answers.
  - `tts.py`: Local text-to-speech via `pyttsx3`.
- **`llm_client/`**:
  - Pluggable LLM client supporting OpenAI, Groq, and Ollama via `LLM_PROVIDER`.
- **`prompts/`**:
  - `role_extraction_prompt.py`: System prompt for role detection.
  - `evaluation_prompt.py`: System prompt for answer evaluation and scoring.
- **`app.py`**:
  - Streamlit UI and orchestration layer.
  - Coordinates parsing, role detection, interview loop, evaluation, and reporting.

### How RAG Is Used

- The `vector_store.InterviewVectorStore` uses:
  - **Chroma** as the vector database (persistent on disk).
  - **Sentence Transformers** (`all-MiniLM-L6-v2` by default) for embeddings.
- Each question is stored with:
  - `question`: the question text (document).
  - `role`: target role (metadata).
  - `difficulty`: difficulty level (metadata).
  - `ideal_answer`: reference answer used for evaluation (metadata).
  - `expected_concepts`: list of key concepts (metadata).
- The interview engine:
  - Queries the vector store with a synthetic query like
    `"Technical interview question for role: <role>"`.
  - Uses metadata filter `where={"role": role}` to ensure role-specific questions.
  - Tracks and excludes already-asked question IDs to avoid repeats.

### Role-Based Evaluation Logic

- For each answered question:
  - `evaluation_engine.AnswerEvaluator.evaluate_answer` sends a structured JSON payload to the LLM
    containing:
    - Role name.
    - Question text.
    - Ideal answer.
    - Expected concepts.
    - Candidate's answer.
  - The LLM responds with strict JSON:
    - `score`: integer in `{0, 1, 2}`.
    - `reasoning`: explanation for the score.
    - `strengths`: list of positive points.
    - `weaknesses`: list of negative points.
  - The interview session stores these per question.
- Role-wise scoring:
  - For each role, all question scores are summed:
    - `total_raw_score = sum(per-question scores)`.
    - `max_possible = number_of_questions_for_role * 2`.
    - `normalized_score = (total_raw_score / max_possible) * 10`.
  - `report_generator.generate_report` returns role-wise summaries with the normalized score out of 10.

### Installation

1. **Create and activate a virtual environment (recommended)**.
2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Set environment variables**:
   - **LLM provider configuration**:
     - `LLM_PROVIDER` in `{"openai", "groq", "ollama"}` (default: `openai`).
     - `LLM_MODEL` (e.g., `gpt-4o-mini` or a Groq/Ollama model name).
     - `LLM_TEMPERATURE` (optional, default `0.2`).
   - For **OpenAI**:
     - `OPENAI_API_KEY`
   - For **Groq**:
     - `GROQ_API_KEY`
   - For **Ollama**:
     - Optional: `OLLAMA_API_URL` (default: `http://localhost:11434/v1/chat/completions`).

4. **Optional audio configuration**:
   - `WHISPER_MODEL` to select the local Whisper model variant (default: `base`).

### Initializing the Vector Database

The vector database must be initialized with sample interview questions before running the app:

```bash
python -m vector_store.init_vector_store
```

This will:
- Create a persistent Chroma database under `vector_store/chroma_db`.
- Insert a curated set of questions for example roles:
  - Backend Engineer
  - Data Scientist
  - ML Engineer

You can extend this by editing `vector_store/init_vector_store.py` and adding more `QuestionRecord`s.

### Running the Streamlit App

Once dependencies are installed and the vector store is seeded:

```bash
streamlit run app.py
```

### Using the Application

1. **Upload Resume**:
   - Upload a PDF or DOCX resume file.
   - The app parses and cleans the text via `resume_parser`.
2. **Role Detection**:
   - Click “Analyze Resume”.
   - The `role_extractor` calls the configured LLM with a structured prompt and returns up to 2 roles.
   - The detected roles, confidence, and rationale are displayed.
3. **Start Interview**:
   - Click “Start Interview” to create an `InterviewSession`.
   - The session decides:
     - 1 role → 10 questions.
     - 2 roles → 5 questions per role.
4. **Answering Questions**:
   - For each question:
     - You can type an answer in the text area.
     - Or upload an audio file (wav/mp3/m4a) to be transcribed by Whisper.
   - Click “Submit Answer” to:
     - Evaluate the answer via the LLM.
     - Immediately see the score (0–2) plus reasoning, strengths, and weaknesses.
   - The app moves on to the next question until all 10 are completed.
5. **View Results**:
   - Once the interview is complete, the app displays:
     - Role-wise scores out of 10.
     - Per-role strengths and weaknesses summary.
     - Total number of questions asked.

### Extensibility

- **Adding new roles and questions**:
  - Update `vector_store/init_vector_store.py` with additional `QuestionRecord` instances.
  - Re-run the initialization script to seed the updated question set.
- **Changing the embedding model**:
  - Set `EMBEDDING_MODEL` in the environment to any Sentence Transformers model name.
- **Switching LLM providers**:
  - Set `LLM_PROVIDER` to `openai`, `groq`, or `ollama` and configure the associated environment variables.
- **Custom prompts**:
  - Modify `prompts/role_extraction_prompt.py` and `prompts/evaluation_prompt.py` to adapt the interviewing style or scoring rubric.

