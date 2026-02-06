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
            q(
                "backend_5",
                "What is a load balancer and how does it improve reliability?",
                "Backend Engineer",
                "easy",
                "A load balancer distributes traffic across multiple servers to prevent overload and single points of failure. It improves availability, enables horizontal scaling, and can perform health checks to route around unhealthy instances.",
                ["load balancer", "availability", "health checks", "scaling"],
            ),
            q(
                "backend_6",
                "Explain caching strategies and common pitfalls.",
                "Backend Engineer",
                "medium",
                "Caching reduces latency by storing frequent data in faster storage. Strategies include write-through, write-back, and cache-aside. Pitfalls include stale data, cache stampede, and poor eviction policies.",
                ["cache", "write-through", "cache-aside", "staleness", "eviction"],
            ),
            q(
                "backend_7",
                "How do you ensure idempotency in APIs?",
                "Backend Engineer",
                "medium",
                "Idempotency ensures repeated requests produce the same result. Techniques include using idempotency keys, conditional updates, and designing PUT/DELETE semantics carefully.",
                ["idempotency", "idempotency key", "PUT", "DELETE"],
            ),
            q(
                "backend_8",
                "What is eventual consistency and when is it acceptable?",
                "Backend Engineer",
                "medium",
                "Eventual consistency means replicas converge over time rather than instantly. It is acceptable when availability and partition tolerance are prioritized and temporary stale reads are acceptable, such as in social feeds or analytics.",
                ["eventual consistency", "replication", "CAP", "stale reads"],
            ),
            q(
                "backend_9",
                "Describe how database indexing works and its trade-offs.",
                "Backend Engineer",
                "medium",
                "Indexes speed up reads by creating data structures like B-trees or hash indexes, but they increase storage usage and slow down writes due to index maintenance.",
                ["index", "B-tree", "query performance", "write overhead"],
            ),
            q(
                "backend_10",
                "What are common causes of N+1 query problems and how do you fix them?",
                "Backend Engineer",
                "medium",
                "N+1 occurs when a query for a list triggers additional queries per item. Fix with joins, eager loading, batching, or caching to reduce round trips.",
                ["N+1", "joins", "eager loading", "batching"],
            ),
            q(
                "backend_11",
                "Explain rate limiting strategies for APIs.",
                "Backend Engineer",
                "medium",
                "Rate limiting controls traffic to protect services. Common approaches include token bucket, leaky bucket, and fixed window counters, often enforced at gateways.",
                ["rate limiting", "token bucket", "leaky bucket", "gateway"],
            ),
            q(
                "backend_12",
                "What is the difference between a monolith and microservices?",
                "Backend Engineer",
                "easy",
                "A monolith is a single deployable unit; microservices split functionality into independently deployable services. Microservices improve scalability and team autonomy but add complexity in networking, observability, and data consistency.",
                ["monolith", "microservices", "deployment", "observability"],
            ),
            q(
                "backend_13",
                "How would you design a URL shortening service?",
                "Backend Engineer",
                "hard",
                "Use a unique ID generator (e.g., base62), store mappings in a database, add caching for hot links, and plan for scalability with sharding and replication. Handle collisions and rate limits.",
                ["system design", "ID generation", "base62", "scaling", "cache"],
            ),
            q(
                "backend_14",
                "What is a circuit breaker and why is it useful?",
                "Backend Engineer",
                "medium",
                "A circuit breaker stops calls to failing services to prevent cascading failures. It monitors error rates and opens to fail fast, then allows recovery with half-open probes.",
                ["circuit breaker", "resilience", "cascading failure"],
            ),
            q(
                "backend_15",
                "Explain optimistic vs pessimistic locking.",
                "Backend Engineer",
                "medium",
                "Optimistic locking assumes low contention and uses version checks; pessimistic locking blocks access to prevent conflicts. Optimistic improves concurrency but requires retries.",
                ["locking", "optimistic", "pessimistic", "concurrency"],
            ),
            q(
                "backend_16",
                "How do you secure APIs?",
                "Backend Engineer",
                "medium",
                "Use authentication (OAuth/JWT), authorization checks, TLS, input validation, rate limiting, and logging. Protect against common attacks like injection and CSRF.",
                ["authentication", "authorization", "TLS", "validation", "security"],
            ),
            q(
                "backend_17",
                "What is CQRS and when would you use it?",
                "Backend Engineer",
                "hard",
                "CQRS separates read and write models to optimize each. It is useful for complex domains with different scaling needs for reads and writes, but adds complexity.",
                ["CQRS", "read model", "write model", "scaling"],
            ),
            q(
                "backend_18",
                "Explain how pagination should be designed for large datasets.",
                "Backend Engineer",
                "medium",
                "Use cursor-based pagination for stable ordering and performance. Offset-based pagination is simpler but can be slow and inconsistent with concurrent writes.",
                ["pagination", "cursor", "offset", "consistency"],
            ),
            q(
                "backend_19",
                "What is a deadlock and how do you avoid it?",
                "Backend Engineer",
                "medium",
                "Deadlock occurs when transactions wait on each other. Avoid with consistent lock ordering, timeouts, smaller transactions, or deadlock detection and retries.",
                ["deadlock", "transactions", "lock ordering", "timeouts"],
            ),
            q(
                "backend_20",
                "Describe blue-green vs canary deployments.",
                "Backend Engineer",
                "medium",
                "Blue-green uses two full environments to switch traffic instantly. Canary gradually shifts traffic to the new version to reduce risk. Both help reduce downtime and rollbacks.",
                ["deployment", "blue-green", "canary", "rollback"],
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
            q(
                "ds_5",
                "What is regularization and why is it useful?",
                "Data Scientist",
                "easy",
                "Regularization adds a penalty to model complexity to reduce overfitting. L1 encourages sparsity, L2 shrinks coefficients.",
                ["regularization", "L1", "L2", "overfitting"],
            ),
            q(
                "ds_6",
                "Explain precision vs recall and when you would prioritize each.",
                "Data Scientist",
                "easy",
                "Precision measures correctness of positive predictions, recall measures coverage of actual positives. Prioritize recall for critical misses (fraud, disease) and precision when false positives are costly.",
                ["precision", "recall", "false positives", "false negatives"],
            ),
            q(
                "ds_7",
                "What is feature scaling and when is it required?",
                "Data Scientist",
                "easy",
                "Feature scaling normalizes features to a common range. It is important for distance-based models and gradient-based optimization, such as kNN, SVM, and linear models.",
                ["feature scaling", "normalization", "standardization"],
            ),
            q(
                "ds_8",
                "Explain the difference between supervised and unsupervised learning.",
                "Data Scientist",
                "easy",
                "Supervised learning uses labeled data to predict targets; unsupervised learning finds structure without labels, such as clustering or dimensionality reduction.",
                ["supervised", "unsupervised", "labels", "clustering"],
            ),
            q(
                "ds_9",
                "How do you detect and handle outliers?",
                "Data Scientist",
                "medium",
                "Use statistical methods (IQR, z-score), model-based methods, or visualization. Handle by removal, capping, or using robust models depending on context.",
                ["outliers", "IQR", "z-score", "robust"],
            ),
            q(
                "ds_10",
                "What is A/B testing and what are common pitfalls?",
                "Data Scientist",
                "medium",
                "A/B testing compares two variants with randomized control to measure impact. Pitfalls include peeking, low power, multiple testing, and biased sampling.",
                ["A/B testing", "randomization", "power", "bias"],
            ),
            q(
                "ds_11",
                "Explain logistic regression and how it differs from linear regression.",
                "Data Scientist",
                "easy",
                "Logistic regression models probability with a sigmoid and is used for classification, while linear regression predicts continuous values. Loss functions differ (log loss vs MSE).",
                ["logistic regression", "linear regression", "classification", "sigmoid"],
            ),
            q(
                "ds_12",
                "What is PCA and why is it used?",
                "Data Scientist",
                "medium",
                "PCA reduces dimensionality by projecting data onto components that maximize variance. It helps with noise reduction and visualization.",
                ["PCA", "dimensionality reduction", "variance"],
            ),
            q(
                "ds_13",
                "How do you choose evaluation metrics for a regression problem?",
                "Data Scientist",
                "easy",
                "Use MAE, MSE, RMSE, and R2. The choice depends on sensitivity to outliers and interpretability requirements.",
                ["MAE", "MSE", "RMSE", "R2"],
            ),
            q(
                "ds_14",
                "What is data leakage and how do you prevent it?",
                "Data Scientist",
                "medium",
                "Data leakage occurs when training data includes information not available at inference time. Prevent by proper splits, time-aware validation, and careful feature engineering.",
                ["data leakage", "validation", "features", "time split"],
            ),
            q(
                "ds_15",
                "Explain ROC curve and PR curve differences.",
                "Data Scientist",
                "medium",
                "ROC shows TPR vs FPR, PR shows precision vs recall. PR is more informative for imbalanced datasets.",
                ["ROC", "PR curve", "TPR", "FPR", "imbalance"],
            ),
            q(
                "ds_16",
                "How would you handle missing data?",
                "Data Scientist",
                "medium",
                "Handle missing values by deletion, imputation (mean/median/model-based), or using algorithms that support missingness. Consider missingness mechanism.",
                ["missing data", "imputation", "MCAR", "MAR"],
            ),
            q(
                "ds_17",
                "Describe k-means clustering and its limitations.",
                "Data Scientist",
                "medium",
                "K-means partitions data into k clusters minimizing within-cluster distance. Limitations include sensitivity to k, initialization, and non-spherical clusters.",
                ["k-means", "clustering", "initialization", "limitations"],
            ),
            q(
                "ds_18",
                "What is the purpose of a validation set?",
                "Data Scientist",
                "easy",
                "A validation set is used to tune hyperparameters and select models without biasing the final test evaluation.",
                ["validation set", "hyperparameters", "model selection"],
            ),
            q(
                "ds_19",
                "Explain model calibration.",
                "Data Scientist",
                "medium",
                "Calibration measures how well predicted probabilities reflect true outcome frequencies. Techniques include Platt scaling and isotonic regression.",
                ["calibration", "probabilities", "Platt scaling"],
            ),
            q(
                "ds_20",
                "What is the difference between bagging and boosting?",
                "Data Scientist",
                "medium",
                "Bagging trains models independently to reduce variance (e.g., Random Forest). Boosting trains sequentially to reduce bias (e.g., XGBoost).",
                ["bagging", "boosting", "variance", "bias"],
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
            q(
                "ml_4",
                "What is model versioning and why is it important?",
                "ML Engineer",
                "easy",
                "Model versioning tracks models, data, and parameters to ensure reproducibility, rollback, and auditability in production systems.",
                ["model versioning", "reproducibility", "rollback"],
            ),
            q(
                "ml_5",
                "Explain the difference between offline and online feature computation.",
                "ML Engineer",
                "medium",
                "Offline features are precomputed in batch, while online features are computed at request time. Consistency between them is crucial to avoid training-serving skew.",
                ["feature computation", "offline", "online", "skew"],
            ),
            q(
                "ml_6",
                "How would you monitor an ML model in production?",
                "ML Engineer",
                "medium",
                "Monitor input drift, prediction distributions, latency, errors, and business KPIs. Use alerts and dashboards; retrain when performance degrades.",
                ["monitoring", "drift", "latency", "KPIs"],
            ),
            q(
                "ml_7",
                "What is training-serving skew and how do you prevent it?",
                "ML Engineer",
                "medium",
                "It occurs when training data differs from serving data due to feature pipelines or data timing. Prevent with shared feature code and validation checks.",
                ["training-serving skew", "features", "validation"],
            ),
            q(
                "ml_8",
                "Explain how model quantization helps deployment.",
                "ML Engineer",
                "medium",
                "Quantization reduces precision to shrink model size and improve latency, often with minimal accuracy loss, making deployment on edge or high-throughput systems easier.",
                ["quantization", "latency", "model size", "deployment"],
            ),
            q(
                "ml_9",
                "What is a feature store and why use one?",
                "ML Engineer",
                "medium",
                "A feature store centralizes feature definitions for reuse across training and serving, improving consistency and reducing duplication.",
                ["feature store", "reuse", "consistency"],
            ),
            q(
                "ml_10",
                "Describe how you would implement batch inference.",
                "ML Engineer",
                "medium",
                "Batch inference runs predictions on large datasets using scheduled jobs. It requires efficient data pipelines, checkpointing, and storage of outputs.",
                ["batch inference", "pipelines", "scheduling"],
            ),
            q(
                "ml_11",
                "How do you handle model rollback in production?",
                "ML Engineer",
                "easy",
                "Use versioned artifacts and deployment strategies like blue-green or canary so you can revert to a previous stable model quickly.",
                ["rollback", "versioning", "deployment"],
            ),
            q(
                "ml_12",
                "What is model drift vs data drift?",
                "ML Engineer",
                "medium",
                "Data drift is a change in input distribution; model drift is a decline in model performance over time. Both require monitoring and retraining strategies.",
                ["data drift", "model drift", "monitoring"],
            ),
            q(
                "ml_13",
                "Explain A/B testing for ML models.",
                "ML Engineer",
                "medium",
                "A/B testing compares models by splitting traffic and evaluating KPIs. It requires careful randomization and sufficient sample size.",
                ["A/B testing", "traffic split", "KPIs"],
            ),
            q(
                "ml_14",
                "How would you ensure low latency for a large model?",
                "ML Engineer",
                "hard",
                "Use model optimization (quantization, distillation), caching, batching, efficient hardware, and autoscaling. Also optimize feature computation.",
                ["latency", "optimization", "distillation", "autoscaling"],
            ),
            q(
                "ml_15",
                "What is a model registry?",
                "ML Engineer",
                "easy",
                "A model registry stores model artifacts, metadata, metrics, and stages (staging/production) for governance and deployment workflows.",
                ["model registry", "metadata", "governance"],
            ),
            q(
                "ml_16",
                "Explain canary deployment for ML models.",
                "ML Engineer",
                "medium",
                "Canary deployment routes a small percentage of traffic to a new model to validate performance before full rollout.",
                ["canary", "deployment", "validation"],
            ),
            q(
                "ml_17",
                "How do you handle data privacy in ML pipelines?",
                "ML Engineer",
                "medium",
                "Apply access controls, encryption, data minimization, and anonymization. Use audits and comply with relevant regulations.",
                ["privacy", "encryption", "anonymization", "access control"],
            ),
            q(
                "ml_18",
                "What is online learning and when is it useful?",
                "ML Engineer",
                "medium",
                "Online learning updates models incrementally as new data arrives. It is useful for non-stationary environments and real-time adaptation.",
                ["online learning", "streaming", "adaptation"],
            ),
            q(
                "ml_19",
                "Describe how to design a retraining pipeline.",
                "ML Engineer",
                "medium",
                "A retraining pipeline schedules data collection, validation, training, evaluation, and deployment with monitoring and rollback options.",
                ["retraining", "pipeline", "validation", "deployment"],
            ),
            q(
                "ml_20",
                "How do you evaluate model fairness?",
                "ML Engineer",
                "medium",
                "Assess performance across groups using fairness metrics (e.g., demographic parity, equalized odds) and mitigate bias with data or model techniques.",
                ["fairness", "bias", "metrics"],
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

