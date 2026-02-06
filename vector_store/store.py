from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import json
import random

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
        self._answer_collection = self._client.get_or_create_collection(
            name=f"{vector_store_config.collection_name}_answers",
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = SentenceTransformer(embedding_config.model_name)
        self.ensure_answer_collection()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedder.encode(texts, show_progress_bar=False).tolist()

    def add_questions(self, questions: List[QuestionRecord]) -> None:
        ids = [q.id for q in questions]
        documents = [q.question for q in questions]
        metadatas: List[Dict[str, Any]] = []
        answer_metadatas: List[Dict[str, Any]] = []
        answer_documents: List[str] = []
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
            answer_metadatas.append(
                {
                    "role": q.role,
                    "difficulty": q.difficulty,
                    "question": q.question,
                    "expected_concepts": json.dumps(q.expected_concepts),
                }
            )
            answer_documents.append(q.ideal_answer)
        embeddings = self._embed(documents)
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        answer_embeddings = self._embed(answer_documents)
        self._answer_collection.upsert(
            ids=ids,
            documents=answer_documents,
            metadatas=answer_metadatas,
            embeddings=answer_embeddings,
        )

    def ensure_answer_collection(self) -> None:
        """
        Backfill the answer collection from the main question collection if needed.
        """
        try:
            if int(self._answer_collection.count()) > 0:
                return
            if int(self._collection.count()) == 0:
                return
            data = self._collection.get(include=["documents", "metadatas", "ids"])
            ids = list(data.get("ids", []))
            metadatas = list(data.get("metadatas", []))
            if not ids or not metadatas:
                return
            answer_documents = [meta.get("ideal_answer", "") for meta in metadatas]
            answer_metadatas: List[Dict[str, Any]] = []
            for idx, meta in enumerate(metadatas):
                answer_metadatas.append(
                    {
                        "role": meta.get("role", ""),
                        "difficulty": meta.get("difficulty", ""),
                        "question": (data.get("documents", [""])[idx] if data.get("documents") else ""),
                        "expected_concepts": meta.get("expected_concepts", "[]"),
                    }
                )
            answer_embeddings = self._embed(answer_documents)
            self._answer_collection.upsert(
                ids=ids,
                documents=answer_documents,
                metadatas=answer_metadatas,
                embeddings=answer_embeddings,
            )
        except Exception:
            return

    def count(self) -> int:
        return int(self._collection.count())

    def seed_if_empty(self) -> bool:
        """
        Seed the vector store with sample questions if it's empty.
        Returns True if seeding occurred.
        """
        if self.count() > 0:
            return False
        try:
            from .init_vector_store import build_sample_questions
            questions = build_sample_questions()
            if questions:
                self.add_questions(questions)
                return True
        except Exception:
            return False
        return False

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

    def get_random_questions_for_role(
        self,
        role: str,
        n: int,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[QuestionRecord]:
        """
        Retrieve random questions for the given role, excluding already asked IDs.
        """
        exclude_ids = exclude_ids or []
        results = self._collection.get(where={"role": role})
        ids = list(results.get("ids", []))
        documents = list(results.get("documents", []))
        metadatas = list(results.get("metadatas", []))
        pool = []
        for idx, qid in enumerate(ids):
            if qid in exclude_ids:
                continue
            pool.append((qid, documents[idx], metadatas[idx]))
        if not pool:
            return []
        random.shuffle(pool)
        records: List[QuestionRecord] = []
        for qid, doc, meta in pool[:n]:
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
                    role=role,
                    difficulty=meta.get("difficulty", "medium"),
                    ideal_answer=meta.get("ideal_answer", ""),
                    expected_concepts=expected_concepts,
                )
            )
        return records

    def semantic_answer_score(self, question_id: str, candidate_answer: str) -> Dict[str, float]:
        """
        Compare candidate answer against ideal answers stored in the vector DB.
        Returns similarity (0-1) and a mapped score (0-2).
        """
        if not candidate_answer.strip():
            return {"similarity": 0.0, "score": 0.0}

        stored = self._answer_collection.get(ids=[question_id], include=["embeddings"])
        embeddings = stored.get("embeddings", []) if stored else []
        if not embeddings:
            return {"similarity": 0.0, "score": 0.0}
        ideal_embedding = embeddings[0]
        cand_embedding = self._embed([candidate_answer])[0]
        dot = sum(a * b for a, b in zip(ideal_embedding, cand_embedding))
        norm_a = sum(a * a for a in ideal_embedding) ** 0.5
        norm_b = sum(b * b for b in cand_embedding) ** 0.5
        similarity = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

        if similarity >= 0.78:
            score = 2.0
        elif similarity >= 0.6:
            score = 1.0
        else:
            score = 0.0
        return {"similarity": similarity, "score": score}

