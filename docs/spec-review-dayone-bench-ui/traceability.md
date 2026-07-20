# Traceability

| Source | Load-bearing source claim | SPEC landing |
|---|---|---|
| PRODUCT_SPEC UI-FR-001–004 | Discoverable operator surface, onboarding detail, person maintenance, history preservation. | CAP-2, CAP-6; `current-state-gap-matrix.md`; Constraints. |
| PRODUCT_SPEC UI-FR-005–009 | CRUD for roles, tracks, tasks, knowledge, responsibles; protected deletion and report-recipient effect. | CAP-3, CAP-4, CAP-6; Constraints. |
| PRODUCT_SPEC UI-FR-010–013 | Deterministic progress, durable reports, simulated approvals, mutation audit. | CAP-1, CAP-5, CAP-8; Constraints. |
| PRODUCT_SPEC UI-NFR-001–004 | SQLite/local boundary, safety/escaping/confirmation, E2E confidence, localhost trust boundary. | Constraints, Non-goals, CAP-8. |
| BACKOFFICE_SPEC | Required fields/actions, catalog lifecycle table, state boundary, audit/security and acceptance criteria. | CAP-2–CAP-6; `epic-story-implications.md`; Constraints. |
| BENCH_SPEC | Bench personas/journeys, SQLite model, deterministic anti-hallucination boundary, hybrid engine, local integrations. | Why, CAP-1/CAP-5, Constraints, Non-goals. |
| ROADMAP | Local-only operation, UI completion, responsible assignment/edit/removal, date-triggered evaluation. | `change-summary.md`; CAP-2/CAP-4/CAP-5. |
| UX DESIGN | Existing visual language, semantic status, visible actions, dialog/table/form behavior, no decorative or color-only states. | CAP-7; `approval-checklist.md`; `items-must-not-change.md`. |
| UX EXPERIENCE | Information architecture, copy, state patterns, htmx interaction, accessibility floor, responsive breakpoints. | CAP-6/CAP-7; `approval-checklist.md`. |
| Architecture spine AD-1–AD-7 | Bench isolation, SQLite truth, template/instance separation, hybrid orchestration, thin channels, simulated access, immutable projections. | Constraints, CAP-1/CAP-3/CAP-5, Non-goals. |
| Architecture spine AD-8–AD-15 | Explicit lifecycle, actor/audit, separate projections, response contract, navigation, dependency safety, accessibility, storage seam. | CAP-1–CAP-7; `change-summary.md`; `epic-story-implications.md`. |
| ADR 0001 | Bench remains a parallel domain and must not alter onboarding YAML domain. | Constraints and Non-goals. |
| ADR 0002 | Strands conversation and LangGraph fixed cycle remain distinct; deterministic writes. | Constraints. |
| ADR 0003 | SQLite catalog/state and task-template/person-instance separation. | CAP-1/CAP-3; Constraints. |
| ADR 0004 | Teams is a thin channel; service owns logic/state and recipient delivery contract. | CAP-1/CAP-5; Constraints and Non-goals. |
| Implementation context | Current FastAPI/htmx, tools, SQLite schema, destructive task deletion, existing tests. | `current-state-gap-matrix.md`; CAP-8. |
| Adversarial review decisions | Stable person identity, atomic audit success, archive/task/report/notification semantics, migration policy, pytest command, channel tests, and local history policy. | Constraints; `current-state-gap-matrix.md`; `epic-story-implications.md`; `approval-checklist.md`. |

Architecture and UX documents remain adopted companions in the SPEC frontmatter because they contain implementation-shaping invariants that downstream story work must reread.
