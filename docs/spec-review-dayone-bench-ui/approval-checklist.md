# Explicit approval checklist

The reviewer should approve each item before story creation. A checked item means the contract is accepted, not that implementation exists.

- [ ] This is a target implementation contract; current architecture-only branch state is not acceptance evidence.
- [ ] CAP-1–CAP-8 and the six-step foundation sequence are complete enough for story planning.
- [ ] `BENCH_ACTOR` and visible `local-operator` fallback are preserved exactly; tests may override it.
- [ ] People removal is archive-only in the UI, with restore and retained reports/tasks/notifications/audit history.
- [ ] Approval vocabulary is exactly `not_required`, `approval_required`, `pending_simulated`; no granted claim is allowed.
- [ ] Responsible uniqueness is case-insensitive `(track_id,email)` and cross-track reuse is allowed.
- [ ] Task physical deletion is limited to pre-instantiation; instantiated tasks are archived/inactivated with identity retained.
- [ ] SQLite remains authoritative and all channels share `bench/tools` seams.
- [ ] Tracks is persistent navigation; Tasks and Responsibles are discoverable from Track detail.
- [ ] Report saved, notification queued/pending, and notification delivered are independently projected.
- [ ] Accessibility criteria cover dialog semantics, labels, focus, keyboard completion, validation, dynamic feedback, text-plus-color status, 200% zoom, and responsive tables/navigation.
- [ ] Test coverage requirements explicitly include lifecycle, audit, responsible edit/uniqueness, status projection, accessibility, and regression paths.
- [ ] Hosted auth, real provisioning, AWS deployment, DynamoDB implementation, and multi-tenancy remain deferred.
- [ ] No existing source/requirements/UX/architecture/ADR/test document is silently amended by adopting this proposal.
- [ ] The development environment provides an executable `pytest`; absence is a setup defect, not a waived validation condition.
- [ ] Final acceptance includes a real test execution record from that environment.
- [ ] `python -m pytest --version` and `python -m pytest` are the canonical environment checks.
- [ ] A UI-FR-001–UI-FR-013 test matrix exists and is complete.
- [ ] Stable `person_id`, versioned migrations, report recipient snapshots, notification transitions, and archived-task visibility are explicitly implemented and tested.
- [ ] Local history has no automatic deletion and its manual backup/reset procedure is documented.
