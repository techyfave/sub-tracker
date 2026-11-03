"""Synthetic public recommendation examples."""

from typing import Any

from app.api.openapi_responses import (
    PROBLEM_401,
    problem_response,
    response_with_instance,
    validation_example,
)

RECOMMENDATION_EXAMPLE = {
    "id": "60000000-0000-4000-8000-000000000002",
    "recommended_action": "downgrade",
    "rationale": "A lower tier fits observed usage.",
    "versions": {"recommendation_version": 1, "prompt_version": "1.0.0", "schema_version": "1.0"},
    "analysis": {
        "analysis_id": "50000000-0000-4000-8000-000000000002",
        "subscription_id": "40000000-0000-4000-8000-000000000002",
        "status": "completed",
        "completed_at": "2026-10-01T10:00:00Z",
    },
    "uncertainty": {"confidence": "0.91", "level": "low", "reason": None},
    "savings": {
        "monthly": {"amount": "4000.00", "currency": "NGN"},
        "annual": {"amount": "48000.00", "currency": "NGN"},
    },
    "evidence": [
        {
            "id": "70000000-0000-4000-8000-000000000002",
            "evidence_type": "usage",
            "source_table": "usage_events",
            "source_id": "80000000-0000-4000-8000-000000000002",
            "snapshot": {"lower_tier_suitable": True},
            "created_at": "2026-10-01T10:00:00Z",
        }
    ],
    "created_at": "2026-10-01T10:00:00Z",
}


def recommendation_responses(detail: bool = False) -> dict[int | str, dict[str, Any]]:
    path = "/api/v1/recommendations" + ("/60000000-0000-4000-8000-000000000002" if detail else "")
    body = (
        RECOMMENDATION_EXAMPLE
        if detail
        else {
            "items": [RECOMMENDATION_EXAMPLE],
            "pagination": {"page": 1, "page_size": 20, "total_items": 1, "total_pages": 1},
        }
    )
    result: dict[int | str, dict[str, Any]] = {
        200: {"content": {"application/json": {"example": body}}},
        401: response_with_instance(PROBLEM_401, path),
        422: problem_response(
            "Invalid path or filter.",
            validation_example(
                instance=path,
                location=["path", "recommendation_id"] if detail else ["query", "status"],
                message="Input should be a valid UUID"
                if detail
                else "Input should be queued, running, completed or failed",
                error_type="uuid_parsing" if detail else "enum",
            ),
            instance=path,
        ),
    }
    if detail:
        result[404] = problem_response(
            "Missing or foreign recommendation.",
            {
                "type": "https://api.subtracker.dev/problems/not-found",
                "title": "Not Found",
                "status": 404,
                "detail": (
                    "Recommendation with ID '60000000-0000-4000-8000-000000000002' was not found."
                ),
                "instance": path,
            },
            instance=path,
        )
    return result
