import os
from dataclasses import dataclass
from typing import Literal


LLMProvider = Literal["openai", "groq", "ollama"]


@dataclass
class LLMConfig:
    provider: LLMProvider = os.getenv("LLM_PROVIDER", "openai")  # type: ignore[assignment]
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
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


llm_config = LLMConfig()
embedding_config = EmbeddingConfig()
vector_store_config = VectorStoreConfig()
audio_config = AudioConfig()

