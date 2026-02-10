from __future__ import annotations

from typing import Dict, List, Any

from evaluation_engine import RoleEvaluationResult

def generate_report(
    interview_state: Dict[str, Any],
    role_results: List[RoleEvaluationResult],
    final_summary: str = "",
) -> Dict[str, Any]:
    """
    Build a final role-wise report without percentage fields.
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
                "total_raw_score": role_result.total_score,
                "max_possible": role_result.max_possible,
            }
        )

    overall_summary = {
        "roles": report_roles,
        "total_questions": sum(len(v) for v in interview_state.get("questions", {}).values()),
        "final_summary": final_summary,
    }
    if role_results:
        overall_summary["total_raw_score"] = sum(r.total_score for r in role_results)
        overall_summary["max_possible"] = sum(r.max_possible for r in role_results)
    return overall_summary

