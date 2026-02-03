from __future__ import annotations

from typing import Dict, List, Any

from evaluation_engine import RoleEvaluationResult


def _summarize_points(points: List[str], max_items: int = 5) -> List[str]:
    unique: List[str] = []
    for p in points:
        if p not in unique and p.strip():
            unique.append(p.strip())
        if len(unique) >= max_items:
            break
    return unique


def generate_report(
    interview_state: Dict[str, Any],
    role_results: List[RoleEvaluationResult],
) -> Dict[str, Any]:
    """
    Build a final role-wise report including normalized scores and
    summarized strengths/weaknesses.
    """
    report_roles: List[Dict[str, Any]] = []
    roles_meta = interview_state.get("roles", {})
    for role_result in role_results:
        meta = roles_meta.get(role_result.role_name, {})
        report_roles.append(
            {
                "role_name": role_result.role_name,
                "confidence": meta.get("confidence", None),
                "role_rationale": meta.get("rationale", ""),
                "score_out_of_10": round(role_result.normalized_score, 2),
                "total_raw_score": role_result.total_score,
                "max_possible": role_result.max_possible,
                "strengths": _summarize_points(role_result.strengths),
                "weaknesses": _summarize_points(role_result.weaknesses),
            }
        )

    overall_summary = {
        "roles": report_roles,
        "total_questions": sum(len(v) for v in interview_state.get("questions", {}).values()),
    }
    return overall_summary

