import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv


# Load environment variables from .env at import time so that
# GROQ_API_KEY, LLM_MODEL, etc. are available everywhere.
load_dotenv()


LLMProvider = Literal["groq"]


@dataclass
class LLMConfig:
    # Provider is fixed to Groq; no fallback to OpenAI or Ollama.
    provider: LLMProvider = "groq"
    # Default to a widely-available Groq model; can be overridden via env.
    model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))


@dataclass
class EmbeddingConfig:
    model_name: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


@dataclass
class VectorStoreConfig:
    persist_directory: str = os.getenv(
        "VECTOR_STORE_DIR", "vector_store/chroma_db"
    )
    collection_name: str = os.getenv("VECTOR_COLLECTION_NAME", "interview_questions")


@dataclass
class AudioConfig:
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")


@dataclass
class CodingRoundConfig:
    question_files: list[str] = field(
        default_factory=lambda: [
            p.strip()
            for p in os.getenv(
                "CODING_QUESTION_FILES",
                "data/sde 2.pdf;"
                "data/FOOMO_Fresher_Medium_Coding_Round.pdf",
            ).split(";")
            if p.strip()
        ]
    )


llm_config = LLMConfig()
embedding_config = EmbeddingConfig()
vector_store_config = VectorStoreConfig()
audio_config = AudioConfig()
coding_round_config = CodingRoundConfig()

