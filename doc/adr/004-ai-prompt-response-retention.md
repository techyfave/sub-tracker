# ADR-004: AI Prompt and Response Retention

**Status:** Accepted

## Context

The subscription tracker sends application context and prompts to an external AI provider and receives AI responses. These prompts and responses may contain user-specific subscription information and must have an explicit retention policy.

This ADR concerns **AI prompts and AI responses**.

The retention implementation is an infrastructure policy inside the
**modular monolith**. Storage and deletion mechanisms remain replaceable
behind application-owned interfaces.

## Options considered

1. **Retain indefinitely**
   - Simplifies debugging and historical inspection.
   - Creates unnecessary long-term data exposure and storage.

2. **Retain for 30 days, then delete raw AI content**
   - Provides enough time for MVP debugging and support.
   - Limits long-term exposure.

3. **Do not persist prompts/responses**
   - Minimizes stored sensitive content.
   - Makes debugging, audit of recent AI runs, and incident investigation harder during the MVP.

## Decision

The MVP retains raw AI prompts and raw AI responses for **30 days** from creation.

After 30 days:

- Raw prompt content is permanently deleted.
- Raw response content is permanently deleted.
- Stored provider/model metadata may be retained only where needed for operational metrics and must not contain prompt/response content or direct user secrets.
- If content is retained for an operational reason, it must be anonymized and must not reconstruct the original prompt or response.

### Logs

Application logs must not contain raw prompts, raw responses, API keys, access tokens, or full provider payloads.

Logs may contain non-content metadata such as:

- internal job ID
- user ID where operationally necessary
- provider name
- model name
- status
- duration
- error category

### Backups

Backups containing AI prompt/response content must follow a maximum **30-day retention window**. Backup systems should exclude raw AI content where technically possible. If raw AI content exists in a backup, the backup must expire according to the same 30-day maximum.

Deletion jobs must be idempotent and observable.

### Ownership

The **backend/service owner** owns implementation and enforcement of this retention policy. The product/data owner is responsible for approving policy changes. Any change to the duration or deletion behavior requires an ADR update before implementation.

## Consequences

### Positive

- Gives the MVP a concrete and enforceable retention period.
- Limits long-term storage of user-specific AI content.
- Prevents raw prompts/responses from becoming normal application logs.
- Defines behavior for backups rather than leaving a major gap.
- Makes policy ownership explicit.

### Negative

- Historical AI conversations older than 30 days cannot be recovered.
- Deletion and backup lifecycle jobs add operational work.
- Debugging older AI failures may require non-content metrics rather than original payloads.
