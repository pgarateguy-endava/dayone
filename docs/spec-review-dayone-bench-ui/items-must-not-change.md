# Items that must not be silently changed

These are preservation locks for downstream story creation and implementation review:

- `BENCH_ACTOR` is the actor source, with visible `local-operator` fallback; tests may override it.
- UI person removal is archive-only. It must not become hard delete or cascade deletion.
- Approval states are only `not_required`, `approval_required`, and `pending_simulated`; submission is not grant.
- Responsible uniqueness is case-insensitive `(track_id, email)`; a responsible can serve multiple tracks.
- A task can be physically deleted only before any person instantiation. After instantiation, archive/inactivate it and retain historical identity and state.
- SQLite is the local Bench source of truth. Bench must not revert to YAML or make rendered Markdown authoritative.
- UI, API, Teams, CLI, and scheduled flows share `bench/tools`; business rules must not move into a channel.
- Hosted authentication, real provisioning, AWS deployment, DynamoDB implementation, and multi-tenancy are deferred.
- The localhost trust boundary remains explicit; this slice is not a hosted employee-facing backoffice.
- Persistent Tracks navigation is required. Tasks and Responsibles remain discoverable from Track detail.
- Report save, notification queue/pending, and notification delivery remain separate projections.
- Native semantic/accessibility behavior and responsive table/navigation rules are acceptance requirements, not optional polish.
- An executable `pytest` is a required development-environment prerequisite; missing tooling is a setup defect and cannot be treated as waived validation.
- `person_id` is the durable person identity; email edits must not rewrite historical references.
- Reports remain file-backed for the MVP, with SQLite metadata and recipient snapshots; files are projections of report records, not permission to conflate save and delivery.
- Archived people remain dependencies for role/track deletion, and local history is not automatically deleted.
- The current implementation verdict remains “incomplete and not acceptance-ready” until implementation and tests prove otherwise.
- No requirement, UX, architecture, ADR, source, or test file may be modified as part of adopting this proposal without an explicit follow-up change.
