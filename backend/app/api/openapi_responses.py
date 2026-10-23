"""Reusable OpenAPI response documentation for Sub Tracker."""

import copy
from typing import Any

PROBLEM_MEDIA_TYPE = "application/problem+json"

SAMPLE_SUBSCRIPTION_ID = "00000000-0000-0000-0000-000000000001"
SAMPLE_SUBSCRIPTION_PATH = f"/api/v1/subscriptions/{SAMPLE_SUBSCRIPTION_ID}"
SAMPLE_TRANSACTION_PATH = f"{SAMPLE_SUBSCRIPTION_PATH}/transactions"
SAMPLE_USAGE_EVENT_PATH = "/api/v1/subscriptions/usage-events"


def validation_example(
    *,
    instance: str,
    location: list[str],
    message: str,
    error_type: str = "value_error",
) -> dict[str, Any]:
    """Build a representative validation Problem Details example."""
    return {
        "type": "https://api.subtracker.dev/problems/validation-error",
        "title": "Validation Error",
        "status": 422,
        "detail": "The request contains invalid data.",
        "instance": instance,
        "errors": [
            {
                "location": location,
                "message": message,
                "type": error_type,
            }
        ],
    }


VALIDATION_ERROR_EXAMPLE = validation_example(
    instance="/api/v1/resource",
    location=["body", "field"],
    message="Input does not match the required format.",
)

REFRESH_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance="/api/v1/auth/refresh",
    location=["body", "refresh_token"],
    message="Field required",
    error_type="missing",
)

CONSENT_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance="/api/v1/consents",
    location=["body", "scope"],
    message="Input should be a valid consent scope",
)

SUBSCRIPTION_LIST_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance="/api/v1/subscriptions",
    location=["query", "limit"],
    message="Input should be greater than or equal to 1",
    error_type="greater_than_equal",
)

SUBSCRIPTION_PATH_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance=SAMPLE_SUBSCRIPTION_PATH,
    location=["path", "id"],
    message="Input should be a valid UUID",
    error_type="uuid_parsing",
)

TRANSACTION_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance=SAMPLE_TRANSACTION_PATH,
    location=["path", "id"],
    message="Input should be a valid UUID",
    error_type="uuid_parsing",
)

USAGE_EVENT_VALIDATION_ERROR_EXAMPLE = validation_example(
    instance=SAMPLE_USAGE_EVENT_PATH,
    location=["body", "idempotency_key"],
    message="Field required",
    error_type="missing",
)

UNAUTHORIZED_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 401,
    "detail": "Authentication is required.",
    "instance": "/api/v1/resource",
}

FORBIDDEN_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 403,
    "detail": "You are not allowed to access this resource.",
    "instance": "/api/v1/resource",
}

NOT_FOUND_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 404,
    "detail": "The requested resource was not found.",
    "instance": "/api/v1/resource/{id}",
}

CONFLICT_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 409,
    "detail": "The request conflicts with existing resource state.",
    "instance": "/api/v1/resource",
}

BAD_REQUEST_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 400,
    "detail": "The requested state transition is not allowed.",
    "instance": "/api/v1/resource/{id}",
}

INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE = {
    "type": "https://api.subtracker.dev/problems/invalid-subscription-reference",
    "title": "Invalid subscription reference",
    "status": 422,
    "detail": "Plan is unavailable",
    "instance": "/api/v1/subscriptions",
}

UNPROCESSABLE_REFERENCE_EXAMPLE = {
    "type": "about:blank",
    "title": "HTTP Error",
    "status": 422,
    "detail": "A referenced resource or subscription date is invalid.",
    "instance": SAMPLE_SUBSCRIPTION_PATH,
}

SERVICE_UNAVAILABLE_EXAMPLE = {
    "type": "about:blank",
    "title": "Service Unavailable",
    "status": 503,
    "detail": "The service is not ready to handle requests.",
    "instance": "/api/v1/health/ready",
}


def problem_response(
    description: str,
    example: dict[str, Any],
    *,
    instance: str | None = None,
    examples: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an OpenAPI Problem Details response with optional named examples."""
    default_example = {**example}
    if instance is not None:
        default_example["instance"] = instance

    content: dict[str, Any] = {
        "schema": {
            "type": "object",
            "required": ["type", "title", "status", "detail", "instance"],
            "properties": {
                "type": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "integer"},
                "detail": {"type": "string"},
                "instance": {"type": "string"},
                "errors": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        }
    }

    if examples:
        named_examples: dict[str, Any] = {}
        for name, value in examples.items():
            example_value = {**value}
            if instance is not None:
                example_value["instance"] = instance
            named_examples[name] = {
                "summary": name.replace("_", " ").capitalize(),
                "value": example_value,
            }
        content["examples"] = named_examples
    else:
        content["example"] = default_example

    return {
        "description": description,
        "content": {PROBLEM_MEDIA_TYPE: content},
    }


def response_with_instance(
    response: dict[str, Any],
    instance: str,
) -> dict[str, Any]:
    """Return a copy of a Problem Details response with a specific instance path."""

    updated = copy.deepcopy(response)

    for media_content in updated.get("content", {}).values():
        if not isinstance(media_content, dict):
            continue

        example = media_content.get("example")
        if isinstance(example, dict):
            example["instance"] = instance

        named_examples = media_content.get("examples", {})
        if isinstance(named_examples, dict):
            for named_example in named_examples.values():
                if not isinstance(named_example, dict):
                    continue

                value = named_example.get("value")
                if isinstance(value, dict):
                    value["instance"] = instance

    return updated


PROBLEM_400 = problem_response(
    "Invalid operation or lifecycle transition.",
    BAD_REQUEST_EXAMPLE,
)
PROBLEM_401 = problem_response(
    "Authentication is missing or invalid.",
    UNAUTHORIZED_EXAMPLE,
)
PROBLEM_403 = problem_response(
    "Access to this resource is forbidden.",
    FORBIDDEN_EXAMPLE,
)
PROBLEM_404 = problem_response(
    "The requested resource was not found.",
    NOT_FOUND_EXAMPLE,
)
PROBLEM_409 = problem_response(
    "The request conflicts with existing state.",
    CONFLICT_EXAMPLE,
)
PROBLEM_422 = problem_response(
    "The request contains invalid data.",
    VALIDATION_ERROR_EXAMPLE,
)
PROBLEM_422_REFERENCE = problem_response(
    "A referenced resource or subscription date is invalid.",
    UNPROCESSABLE_REFERENCE_EXAMPLE,
)
PROBLEM_503 = problem_response(
    "The service is not ready to handle requests.",
    SERVICE_UNAVAILABLE_EXAMPLE,
)

RATE_LIMIT_RESPONSE = {
    "description": "The request rate limit has been exceeded.",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["error"],
                "properties": {"error": {"type": "string"}},
            },
            "example": {"error": "Rate limit exceeded: 5 per 1 minute"},
        }
    },
}


SUBSCRIPTION_CREATE_422 = problem_response(
    "Invalid subscription request data or subscription reference.",
    VALIDATION_ERROR_EXAMPLE,
    instance="/api/v1/subscriptions",
    examples={
        "validation_error": {
            **VALIDATION_ERROR_EXAMPLE,
            "instance": "/api/v1/subscriptions",
        },
        "plan_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Plan is unavailable",
            "instance": "/api/v1/subscriptions",
        },
        "provider_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Provider is unavailable",
            "instance": "/api/v1/subscriptions",
        },
        "provider_connection_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Provider connection is unavailable",
            "instance": "/api/v1/subscriptions",
        },
        "unsupported_plan_cadence": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Plan cadence is unsupported",
            "instance": "/api/v1/subscriptions",
        },
    },
)

SUBSCRIPTION_ITEM_404 = problem_response(
    "The subscription does not exist or is not accessible to the current user.",
    {
        **NOT_FOUND_EXAMPLE,
        "detail": "Subscription not found",
        "instance": SAMPLE_SUBSCRIPTION_PATH,
    },
    instance="/api/v1/subscriptions/{id}",
)

SUBSCRIPTION_UPDATE_400 = problem_response(
    "The requested subscription lifecycle transition is not allowed.",
    {
        **BAD_REQUEST_EXAMPLE,
        "instance": "/api/v1/subscriptions/{id}",
    },
    instance="/api/v1/subscriptions/{id}",
)

SUBSCRIPTION_UPDATE_422 = problem_response(
    "Invalid subscription update data or subscription reference.",
    VALIDATION_ERROR_EXAMPLE,
    instance="/api/v1/subscriptions/{id}",
    examples={
        "validation_error": {
            **VALIDATION_ERROR_EXAMPLE,
            "instance": "/api/v1/subscriptions/{id}",
        },
        "plan_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Plan is unavailable",
            "instance": "/api/v1/subscriptions/{id}",
        },
        "provider_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Provider is unavailable",
            "instance": "/api/v1/subscriptions/{id}",
        },
        "provider_connection_unavailable": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Provider connection is unavailable",
            "instance": "/api/v1/subscriptions/{id}",
        },
        "unsupported_plan_cadence": {
            **INVALID_SUBSCRIPTION_REFERENCE_EXAMPLE,
            "detail": "Plan cadence is unsupported",
            "instance": "/api/v1/subscriptions/{id}",
        },
    },
)

TRANSACTION_CONFLICT_409 = problem_response(
    "The transaction conflicts with an existing transaction reference.",
    {
        **CONFLICT_EXAMPLE,
        "detail": ("This transaction reference is already associated with another subscription."),
        "instance": SAMPLE_TRANSACTION_PATH,
    },
    instance="/api/v1/subscriptions/{id}/transactions",
    examples={
        "duplicate_reference": {
            **CONFLICT_EXAMPLE,
            "detail": (
                "This transaction reference is already associated with another subscription."
            ),
            "instance": SAMPLE_TRANSACTION_PATH,
        },
        "recording_conflict": {
            **CONFLICT_EXAMPLE,
            "detail": "The transaction could not be recorded safely.",
            "instance": SAMPLE_TRANSACTION_PATH,
        },
    },
)

USAGE_EVENT_CONFLICT_409 = problem_response(
    "The usage event conflicts with an existing idempotency key or payload.",
    {
        **CONFLICT_EXAMPLE,
        "detail": ("This idempotency key was already used with a different usage payload."),
        "instance": SAMPLE_USAGE_EVENT_PATH,
    },
    instance=SAMPLE_USAGE_EVENT_PATH,
    examples={
        "recording_conflict": {
            **CONFLICT_EXAMPLE,
            "detail": "The usage event could not be recorded safely.",
            "instance": SAMPLE_USAGE_EVENT_PATH,
        },
        "unresolved_idempotency_conflict": {
            **CONFLICT_EXAMPLE,
            "detail": "The idempotency conflict could not be resolved safely.",
            "instance": SAMPLE_USAGE_EVENT_PATH,
        },
        "key_belongs_to_another_subscription": {
            **CONFLICT_EXAMPLE,
            "detail": ("This idempotency key is already associated with another subscription."),
            "instance": SAMPLE_USAGE_EVENT_PATH,
        },
        "key_reused_for_different_payload": {
            **CONFLICT_EXAMPLE,
            "detail": ("This idempotency key was already used with a different usage payload."),
            "instance": SAMPLE_USAGE_EVENT_PATH,
        },
    },
)

USAGE_EVENT_422 = problem_response(
    "The usage-event request contains invalid data.",
    USAGE_EVENT_VALIDATION_ERROR_EXAMPLE,
    instance=SAMPLE_USAGE_EVENT_PATH,
)
