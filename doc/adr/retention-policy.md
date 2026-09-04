 Retention Policy


Decision

Generated tokens follows a type-based retention policy.

The retention period is determined by the type and lifecycle of the generated tokens rather than being hard-coded throughout application logic.

For the MVP, generated tokens has a 7-day retention period.

Retention behaviour must be implemented as a replaceable policy so that production requirements can change without modifying the editing domain.

Consequences
Positive
Controls storage growth.
Keeps temporary generated assets from accumulating indefinitely.
Provides predictable MVP behaviour.
Retention rules remain separate from editing logic.
Negative
tokens cleanup must be scheduled and monitored.
Users cannot assume generated token is permanently available.
Storage lifecycle management becomes an operational responsibility.