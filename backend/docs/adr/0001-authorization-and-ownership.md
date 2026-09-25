# ADR 0001: Authorization and Ownership Foundations

## Status

Accepted

## Context

The Subscription Optimization API contains resources that belong to
individual users. Access must be restricted so that users can only
view and modify their own resources.

## Decision

A reusable ownership helper was introduced:

```python
ensure_owner(resource_owner_id, current_user)
```