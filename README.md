## AI Interview Agent

An end-to-end, modular AI-powered technical interview agent built with Python and a custom web frontend.
It parses a candidate's resume, detects up to two suitable technical roles, conducts a structured
interview with exactly 10 questions, evaluates answers using RAG + LLMs, and produces role-wise
percentage scores.

### Architecture Overview

- **`resume_parser/`**: Loads a resume (PDF or DOCX) and converts it into clean text.
- **`role_extractor/`**: Uses an LLM to infer up to 2 suitable technical roles from the resume text.
- **`vector_store/`**:
  - Wraps Chroma with Sentence Transformers embeddings.
  - Stores curated interview questions with metadata.
  - Supports metadata filtering by `role` and similarity search.
- **`interview_engine/`**:
  - `InterviewSession` enforces the interview rules and tracks asked questions.
- **`evaluation_engine/`**:
  - `AnswerEvaluator` scores each answer with semantic similarity in the vector DB.
  - Aggregates per-role scores and computes normalized percentage scores.
- **`report_generator/`**:
  - Builds the final role-wise report with percent scores.
- **`audio_io/`**:
  - `stt.py`: Whisper-based speech-to-text for audio answers.
  - `tts.py`: Local text-to-speech via `pyttsx3`.
- **`llm_client/`**:
  - Pluggable LLM client supporting OpenAI, Groq, and Ollama via `LLM_PROVIDER`.
- **`prompts/`**:
  - Prompt templates for role extraction and answer evaluation.
- **`frontend/`**:
  - Web frontend for interview flow and reporting.

### How RAG Is Used

- The `vector_store.InterviewVectorStore` uses:
  - **Chroma** as the vector database (persistent on disk).
  - **Sentence Transformers** for embeddings.
- Each question is stored with:
  - `question`, `role`, `difficulty`, `ideal_answer`, `expected_concepts`.
- The interview engine:
  - Queries the vector store with a synthetic query like
    `"Technical interview question for role: <role>"`.
  - Filters by `role` to ensure role-specific questions.

### Role-Based Evaluation Logic

- For each answered question:
  - The evaluator computes semantic similarity between the candidate answer and the ideal answer
    stored in the vector DB.
  - The interview session stores per-question percentage scores.
- Role-wise scoring:
  - `total_raw_score = sum(per-question scores)`.
  - `max_possible = number_of_questions_for_role * 100`.
  - `normalized_score = (total_raw_score / max_possible) * 100`.
  - `report_generator.generate_report` returns role-wise summaries with normalized percentage scores.

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

### Running the API

```bash
python -m uvicorn api:app --reload --port 8000
```

### Running the Web Frontend

```bash
cd frontend
python -m http.server 5500
```

### Using the Application

1. **Upload Resume**:
   - Upload a PDF or DOCX resume file.
2. **Role Detection**:
   - Click “Analyze Resume”.
3. **Start Interview**:
   - Click “Start Interview” to create an `InterviewSession`.
4. **Answering Questions**:
   - The interviewer reads each question aloud.
   - After a short delay, the mic records the response for a fixed window.
   - Answers are transcribed and evaluated automatically.
5. **View Results**:
   - The app displays role-wise percentage scores and total questions asked.

### Extensibility

- **Adding new roles and questions**:
  - Update `vector_store/init_vector_store.py` with additional `QuestionRecord` instances.
  - Re-run the initialization script to seed the updated question set.
- **Changing the embedding model**:
  - Set `EMBEDDING_MODEL` in the environment to any Sentence Transformers model name.
- **Switching LLM providers**:
  - Set `LLM_PROVIDER` to `openai`, `groq`, or `ollama` and configure the associated environment variables.
- **Custom prompts**:
  - Modify `prompts/role_extraction_prompt.py` and `prompts/evaluation_prompt.py`.
