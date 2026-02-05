from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import embedding_config, vector_store_config


@dataclass
class QuestionRecord:
    id: str
    question: str
    role: str
    difficulty: str
    ideal_answer: str
    expected_concepts: List[str]


class InterviewVectorStore:
    """
    Thin wrapper around Chroma with sentence-transformer embeddings.
    Stores interview questions with role-based metadata and supports
    similarity search with metadata filtering.
    """

    def __init__(self) -> None:
        self._client = chromadb.Client(
            Settings(
                persist_directory=vector_store_config.persist_directory,
                is_persistent=True,
            )
        )
        self._collection = self._client.get_or_create_collection(
            name=vector_store_config.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = SentenceTransformer(embedding_config.model_name)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedder.encode(texts, show_progress_bar=False).tolist()

    def add_questions(self, questions: List[QuestionRecord]) -> None:
        ids = [q.id for q in questions]
        documents = [q.question for q in questions]
        metadatas: List[Dict[str, Any]] = []
        for q in questions:
            metadatas.append(
                {
                    "role": q.role,
                    "difficulty": q.difficulty,
                    "ideal_answer": q.ideal_answer,
                    # Chroma metadata values must be scalar; store list as JSON string.
                    "expected_concepts": json.dumps(q.expected_concepts),
                }
            )
        embeddings = self._embed(documents)
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def get_questions_for_role(
        self,
        role: str,
        n: int,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[QuestionRecord]:
        """
        Retrieve `n` questions for the given role, using similarity search
        against a simple role description prompt. Excludes any question IDs
        in `exclude_ids`.
        """
        exclude_ids = exclude_ids or []
        # Use a synthetic query based on role; questions are already curated.
        query_text = f"Technical interview question for role: {role}"
        query_embedding = self._embed([query_text])[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n + len(exclude_ids),
            where={"role": role},
        )

        # Fallback: if role has no questions (e.g. "General Technical Candidate"),
        # try other roles so the interview can proceed.
        display_role = role
        if not results.get("ids") or not results["ids"][0]:
            fallback_roles = ["Backend Engineer", "Data Scientist", "ML Engineer"]
            for fb_role in fallback_roles:
                if fb_role == role:
                    continue
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n + len(exclude_ids),
                    where={"role": fb_role},
                )
                if results.get("ids") and results["ids"][0]:
                    display_role = role  # Keep original role for display/reporting
                    break

        records: List[QuestionRecord] = []
        ids_list = results.get("ids", [[]])[0] or []
        for idx, qid in enumerate(ids_list):
            if qid in exclude_ids:
                continue
            doc = results["documents"][0][idx]
            meta = results["metadatas"][0][idx]
            raw_concepts = meta.get("expected_concepts", "[]")
            if isinstance(raw_concepts, str):
                try:
                    expected_concepts = json.loads(raw_concepts)
                except json.JSONDecodeError:
                    expected_concepts = [raw_concepts]
            else:
                expected_concepts = list(raw_concepts)
            records.append(
                QuestionRecord(
                    id=qid,
                    question=doc,
                    role=display_role,
                    difficulty=meta["difficulty"],
                    ideal_answer=meta["ideal_answer"],
                    expected_concepts=expected_concepts,
                )
            )
            if len(records) >= n:
                break
        return records

