# Change summary

## Proposal status

- Architecture: approved for story planning.
- Implementation: incomplete; not ready for final acceptance testing.
- Branch evidence: architecture documentation only; this proposal applies no UI completion code.
- Validation: `pytest` was not run because it is unavailable in the worktree. This is a development-environment defect to resolve before implementation validation; existing tests are not evidence for the new seams.

## Contract changes from the current implementation

1. Add schema/migrations for lifecycle/archive fields, append-only audit records, durable report records, and explicit notification/projection status.
2. Route every mutation through actor-aware shared tools and audit the mutation outcome.
3. Replace person/task destructive behavior with archive/inactivation and history preservation.
4. Add people edit/archive/restore/listing behavior and responsible edit plus uniqueness validation.
5. Add explicit simulated approval projection and independent report-save/notification status projections.
6. Make Tracks persistent navigation and expose task/responsible administration from Track detail.
7. Finish dialog semantics, active navigation, labels, focus/feedback behavior, status text, keyboard paths, zoom, and responsive table/navigation behavior.
8. Add unit, API, UI, lifecycle, regression, accessibility, and end-to-end acceptance coverage; require an executable `pytest` environment before validation.

## Foundation sequence

1. Schema/migrations and shared mutation/audit seams.
2. People lifecycle and task-history safety.
3. Responsible CRUD and report/notification projections.
4. Navigation and remaining catalog CRUD.
5. Accessibility/responsive behavior.
6. End-to-end and regression coverage.

Sequence is a dependency order: later polish and coverage must not conceal missing durable seams.
