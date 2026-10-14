# 0003: Subscription date and lifecycle rules

## Status
Accepted

## Rules
- renewal_at must not be before started_at.
- ended_at must not be before started_at.
- Dates are checked on create and, for PATCH, on the final stored state after the change is applied.
- A rejected request changes nothing in the database.
- Status transitions follow the table in the subscription entity.
- Invalid dates return a 422 Problem Details response.
Status: only cancelled -> paused is rejected. All other status changes are allowed.”

## Why
A PATCH may send only one field, so the combined state is the only reliable thing to check.
