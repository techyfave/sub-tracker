from __future__ import annotations

from typing import Any

from app.main import app

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_STATUS_CODES = {"400", "401", "403", "404", "409", "422"}
PROBLEM_REQUIRED_FIELDS = {"type", "title", "status", "detail", "instance"}


def main() -> None:
    schema = app.openapi()
    errors: list[str] = []

    target_prefixes = (
        "/api/v1/subscriptions",
        "/api/v1/consents",
        "/api/v1/health",
        "/api/v1/auth",
        "/api/v1/me",
    )
    methods = {"get", "post", "put", "patch", "delete"}

    print("OPENAPI RESPONSE AUDIT")

    for path in sorted(schema["paths"]):
        if not path.startswith(target_prefixes):
            continue

        for method, operation in sorted(schema["paths"][path].items()):
            if method.lower() not in methods:
                continue

            operation_name = f"{method.upper()} {path}"
            responses = operation.get("responses", {})

            # Print the operation and its responses on separate lines.
            print()
            print(operation_name)
            print(f"Responses: {', '.join(sorted(responses))}")

            if not responses:
                errors.append(f"{operation_name}: no documented responses")
                continue

            for code, response in sorted(responses.items()):
                content = response.get("content", {})

                if code == "204":
                    if content:
                        errors.append(f"{operation_name}: 204 must not define a body")
                    print("  204 body:", "present" if content else "none")

                for media_type, media in content.items():
                    print(f"  {code} content type: {media_type}")

                    example_values: list[tuple[str, Any]] = []

                    if "example" in media:
                        example_values.append(("example", media["example"]))
                        print(f"    Example: {media['example']}")

                    named_examples = media.get("examples", {})

                    for name, example in sorted(named_examples.items()):
                        displayed_value = (
                            example.get("value") if isinstance(example, dict) else example
                        )
                        print(f"    Example [{name}]: {displayed_value}")

                        if not isinstance(example, dict):
                            errors.append(
                                f"{operation_name} {code}: named example {name!r} must be an object"
                            )
                            continue

                        if "value" not in example:
                            errors.append(
                                f"{operation_name} {code}: named example {name!r} has no value"
                            )
                            continue

                        example_value = example["value"]

                        # The example value must contain the response body
                        # directly, not an extra summary/value wrapper.
                        if (
                            isinstance(example_value, dict)
                            and "type" not in example_value
                            and "value" in example_value
                        ):
                            errors.append(
                                f"{operation_name} {code}: named example "
                                f"{name!r} has a nested value wrapper; "
                                "put the Problem Details object directly "
                                "in the example's value"
                            )
                            continue

                        example_values.append((name, example_value))

                    if code in PROBLEM_STATUS_CODES and media_type == PROBLEM_MEDIA_TYPE:
                        if not example_values:
                            errors.append(
                                f"{operation_name} {code}: Problem Details response has no example"
                            )
                            continue

                        for example_name, value in example_values:
                            if not isinstance(value, dict):
                                errors.append(
                                    f"{operation_name} {code}: example "
                                    f"{example_name!r} is not an object"
                                )
                                continue

                            missing = PROBLEM_REQUIRED_FIELDS - value.keys()
                            if missing:
                                errors.append(
                                    f"{operation_name} {code}: example "
                                    f"{example_name!r} is missing "
                                    f"{', '.join(sorted(missing))}"
                                )

                            if str(value.get("status")) != code:
                                errors.append(
                                    f"{operation_name} {code}: example "
                                    f"{example_name!r} status does not "
                                    "match response"
                                )

    print()

    if errors:
        print("OPENAPI AUDIT FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("OPENAPI SCHEMA AUDIT PASSED")
    print("Note: this script does not verify live HTTP responses.")


if __name__ == "__main__":
    main()
