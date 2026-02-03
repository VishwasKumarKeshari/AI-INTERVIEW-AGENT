from __future__ import annotations

import os
from typing import List

from .store import InterviewVectorStore, QuestionRecord


def build_sample_questions() -> List[QuestionRecord]:
    """
    Seed the vector store with a small but realistic set of questions
    covering a few common technical roles. This can be extended easily.
    """
    questions: List[QuestionRecord] = []

    def q(
        qid: str,
        question: str,
        role: str,
        difficulty: str,
        ideal_answer: str,
        expected_concepts: List[str],
    ) -> QuestionRecord:
        return QuestionRecord(
            id=qid,
            question=question,
            role=role,
            difficulty=difficulty,
            ideal_answer=ideal_answer,
            expected_concepts=expected_concepts,
        )

    # Backend Engineer
    questions.extend(
        [
            q(
                "backend_1",
                "Explain the differences between horizontal and vertical scaling in backend systems.",
                "Backend Engineer",
                "medium",
                "Horizontal scaling adds more machines to handle load, while vertical scaling adds more resources (CPU, RAM) to a single machine. Horizontal scaling improves fault tolerance and elasticity but adds complexity (load balancing, data partitioning). Vertical scaling is simpler but has hardware limits and can be a single point of failure.",
                ["horizontal scaling", "vertical scaling", "fault tolerance", "load balancing"],
            ),
            q(
                "backend_2",
                "What is a database transaction and what are the ACID properties?",
                "Backend Engineer",
                "easy",
                "A transaction is a unit of work performed against a database. ACID stands for Atomicity, Consistency, Isolation, Durability: atomicity ensures all-or-nothing, consistency ensures constraints are preserved, isolation ensures concurrent transactions do not interfere, and durability guarantees committed changes persist after failures.",
                ["transaction", "ACID", "atomicity", "consistency", "isolation", "durability"],
            ),
            q(
                "backend_3",
                "When would you choose a message queue in a backend architecture?",
                "Backend Engineer",
                "medium",
                "Message queues decouple producers and consumers, enabling asynchronous processing, smoothing traffic spikes, and improving reliability. They are used when tasks can be processed later, to prevent overloading downstream services, and to provide retry and buffering semantics.",
                ["message queue", "asynchronous processing", "decoupling", "reliability"],
            ),
            q(
                "backend_4",
                "Compare REST and gRPC for service-to-service communication.",
                "Backend Engineer",
                "hard",
                "REST typically uses JSON over HTTP 1.1 and is human-readable and easy to integrate. gRPC uses Protocol Buffers over HTTP/2, offering strong typing, bi-directional streaming, and better performance. gRPC is better for internal microservices, while REST is more interoperable and web-friendly.",
                ["REST", "gRPC", "protocol buffers", "HTTP/2", "microservices"],
            ),
        ]
    )

    # Data Scientist
    questions.extend(
        [
            q(
                "ds_1",
                "How do you handle class imbalance in a classification problem?",
                "Data Scientist",
                "medium",
                "Techniques include resampling (oversampling minority, undersampling majority), using class weights, choosing appropriate metrics like F1 or AUC, generating synthetic samples with SMOTE, and adjusting decision thresholds. The choice depends on data size and business constraints.",
                ["class imbalance", "resampling", "class weights", "SMOTE", "metrics"],
            ),
            q(
                "ds_2",
                "Explain the bias-variance trade-off.",
                "Data Scientist",
                "easy",
                "Bias measures error from erroneous assumptions; variance measures sensitivity to training data fluctuations. High bias leads to underfitting; high variance leads to overfitting. The goal is to find a balance where total expected error is minimized, often via regularization, model complexity control, or more data.",
                ["bias", "variance", "underfitting", "overfitting", "regularization"],
            ),
            q(
                "ds_3",
                "What is cross-validation and why is it useful?",
                "Data Scientist",
                "easy",
                "Cross-validation partitions data into multiple train/validation splits to estimate generalization performance more robustly. k-fold cross-validation trains k models, each time using a different fold as validation. It reduces variance in performance estimates and helps with model selection and hyperparameter tuning.",
                ["cross-validation", "k-fold", "generalization", "model selection"],
            ),
            q(
                "ds_4",
                "How would you evaluate a binary classifier for a highly imbalanced dataset?",
                "Data Scientist",
                "medium",
                "Use metrics beyond accuracy such as precision, recall, F1-score, ROC-AUC, and PR-AUC. Examine confusion matrices, consider cost of false positives vs false negatives, and possibly use stratified cross-validation. Calibration plots can help assess predicted probability quality.",
                ["precision", "recall", "F1", "ROC-AUC", "PR-AUC", "imbalance"],
            ),
        ]
    )

    # ML Engineer
    questions.extend(
        [
            q(
                "ml_1",
                "Describe an end-to-end ML pipeline from data ingestion to deployment.",
                "ML Engineer",
                "hard",
                "An ML pipeline typically includes data ingestion, validation, feature engineering, model training, evaluation, and packaging. In production, it adds model versioning, CI/CD, automated retraining, monitoring for drift and performance, and interfaces for serving (REST, gRPC, batch). Tools like orchestrators and feature stores are often used.",
                ["data ingestion", "feature engineering", "training", "deployment", "monitoring"],
            ),
            q(
                "ml_2",
                "What is concept drift and how can you detect it?",
                "ML Engineer",
                "medium",
                "Concept drift occurs when the relationship between inputs and target changes over time. Detection methods include monitoring performance metrics, using statistical tests on input or output distributions, drift detectors like DDM or ADWIN, and comparing predictions to delayed ground truth.",
                ["concept drift", "monitoring", "statistical tests", "performance metrics"],
            ),
            q(
                "ml_3",
                "How would you design an online prediction service for a large-scale ML model?",
                "ML Engineer",
                "hard",
                "Key aspects include low-latency model serving (possibly with model quantization or distillation), autoscaling, caching, request batching, feature computation strategy (online vs offline), robust logging, A/B testing, and canary deployments. You also need monitoring for latency, errors, and model performance.",
                ["model serving", "latency", "autoscaling", "feature store", "monitoring"],
            ),
        ]
    )

    return questions


def main() -> None:
    os.makedirs("vector_store", exist_ok=True)
    store = InterviewVectorStore()
    questions = build_sample_questions()
    store.add_questions(questions)
    print(f"Seeded vector store with {len(questions)} questions.")


if __name__ == "__main__":
    main()

