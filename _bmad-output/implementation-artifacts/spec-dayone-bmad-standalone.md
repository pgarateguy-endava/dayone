---
title: 'Make DayOne a child-local BMad project root'
type: 'chore'
created: '2026-07-28'
status: 'done'
baseline_commit: '37a8abc333dfb225be0d9806229dd260d7f081c0'
review_loop_iteration: 0
context:
  - _bmad-output/specs/spec-dayone-bmad-standalone/SPEC.md
  - AGENTS.md
  - docs/development-workflow.md
  - docs/BENCH_SPEC.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** DayOne currently owns its source, documents, and durable BMad outputs, but its BMad runtime configuration and resolver scripts exist only in the hub. Running workflows from the child therefore risks hub-local paths and cannot reliably preserve team artifacts in a clean clone.

**Approach:** Add the minimum team-owned `_bmad/` integration and configuration needed for the installed BMad skill distribution to resolve the child as `{project-root}`. Preserve existing artifacts and personal settings boundaries, validate from the child root, and defer replacement README generation until bootstrap work is complete.

## Boundaries & Constraints

**Always:** Use the post-Story 1.3 `feature/bench` baseline; keep paths relative to the child; preserve `_bmad-output/`, `AGENTS.md`, workflow rules, SQLite authority, and product behavior; keep team configuration committed and personal configuration ignored; use `uv run pytest`; exclude credentials, `.env`, caches, virtual environments, and hub runtime dependencies.

**Ask First:** Stop if the supported installed BMad version or source files have an incompatible license, if a required runtime file cannot be reduced to a child-owned integration, or if validation requires changing product behavior. Confirm the documented external skill/plugin prerequisite before implementation.

**Never:** Vendor the hub `.agents/` skill tree, copy personal configuration, duplicate canonical planning documents, modify Story 1.3 behavior, synchronize SQLite and DynamoDB, or generate/edit the replacement `README.md` during bootstrap planning or implementation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean child resolution | Fresh child checkout plus supported installed skill path | Config and customization resolve under the child and write artifacts under `_bmad-output/` | Fail clearly if required project files or skill path are missing |
| Personal state present | Gitignored user config, `.env`, cache, or local runtime data | Team resolution remains reproducible and personal files remain untracked | Validation reports forbidden tracked or leaked paths |
| Hub path temptation | Resolver invoked from child with hub also available | No resolved path references the hub repository | Treat any hub-local result as a blocker |
| README sequencing | Bootstrap complete, original README preserved | Later README generation uses `docs/BENCH_SPEC.md` and retains the renamed original | Do not generate the replacement README before bootstrap completion |

</frozen-after-approval>

## Code Map

- `_bmad/config.toml` -- child-owned team configuration and project-relative output paths.
- `_bmad/bmm/config.yaml` -- BMM project, language, artifact, and knowledge-path settings.
- `_bmad/scripts/resolve_config.py` -- stdlib resolver used to prove child-root configuration.
- `_bmad/scripts/resolve_customization.py` -- merges installed skill defaults with child team/user overrides.
- `_bmad/_config/` -- manifests and metadata needed by supported workflows, limited to required integration files.
- `_bmad/custom/` -- committed team overrides plus ignored personal override boundary.
- `_bmad-output/specs/spec-dayone-bmad-standalone/` -- preserved starting specification and memory artifacts.
- `docs/development-workflow.md`, `AGENTS.md`, `.gitignore` -- project safety and reproducibility contract.

## Tasks & Acceptance

**Execution:**
- [x] Inventory hub BMad files and licenses, then add only the required child-local runtime/configuration and manifests -- avoid vendoring skills or personal state.
- [x] Configure child-relative project name, languages, planning/implementation artifacts, project knowledge, output folder, and team workflow rules -- make resolution deterministic.
- [x] Preserve and normalize existing BMad outputs, sprint status, stories, specs, memory, and project context -- keep the child as the durable source of truth.
- [x] Update `.gitignore` and concise child documentation for the external skill/plugin prerequisite and validation commands -- prevent credentials, caches, and hub dependencies.
- [x] Run resolver checks and `uv run pytest`, then inspect paths and diff scope -- prove integration without product changes.

**Acceptance Criteria:**
- Given a clean DayOne checkout and the documented supported skill prerequisite, when workflows are invoked from the child root, then configuration and customization resolve without hub-local paths.
- Given existing planning, implementation, sprint, spec, and memory artifacts, when bootstrap files are added, then those artifacts remain discoverable and unchanged except for explicitly required normalization.
- Given personal config, `.env`, caches, or local runtime data, when repository hygiene is checked, then none is committed or exposed by resolver output.
- Given the post-Story 1.3 codebase, when validation runs, then `uv run pytest` passes and no Bench product/storage behavior changes are introduced.
- Given bootstrap is complete, when the later README deliverable begins, then `README.original.md` remains recoverable and the new README is based on `docs/BENCH_SPEC.md`.

## Spec Change Log

## Design Notes

The hub inventory confirms the required project integration already exists at `/home/iassandri/Code/ai-playground/_bmad/`, including config, manifests, and stdlib resolvers, but it also contains personal configuration and the hub project identity. The child implementation should adapt the team-owned contract rather than copy the hub wholesale. Environment-installed skill definitions remain a prerequisite and are intentionally outside this repository.

## Verification

**Commands:**
- `python3 _bmad/scripts/resolve_config.py --project-root "$PWD"` -- expected: all resolved project paths remain inside the child.
- `python3 _bmad/scripts/resolve_customization.py --skill <installed-skill-path> --key workflow` -- expected: team overrides merge without hub references.
- `uv run pytest` -- expected: existing suite passes.
- `git status --short --ignored` -- expected: no credentials, `.env`, cache, virtual environment, or personal BMad config is tracked.

## Suggested Review Order

**Child-root resolution**

- Start with the resolver output contract and child-root path expansion.
  [`resolve_config.py:64`](../../_bmad/scripts/resolve_config.py#L64)

- Then inspect installed-skill customization discovery and team override merging.
  [`resolve_customization.py:64`](../../_bmad/scripts/resolve_customization.py#L64)

**Durable project integration**

- Confirm project-relative artifact ownership and external skill separation.
  [`config.toml:3`](../../_bmad/config.toml#L3)

- Verify recorded runtime metadata does not claim vendored skills.
  [`manifest.yaml:1`](../../_bmad/_config/manifest.yaml#L1)

- Check the contributor prerequisite and validation procedure.
  [`bmad-workflow.md:8`](../../docs/bmad-workflow.md#L8)

**Memory and safety boundaries**

- Review append-only memory operations, atomic writes, and timestamp maintenance.
  [`memlog.py:20`](../../_bmad/scripts/memlog.py#L20)

- Confirm personal configuration and generated-state exclusions.
  [`.gitignore:1`](../../.gitignore#L1)

**Preservation and verification**

- Compare the implementation against the approved starting intent.
  [`SPEC.md:1`](../specs/spec-dayone-bmad-standalone/SPEC.md#L1)

- Confirm the original README remains recoverable for the post-bootstrap deliverable.
  [`README.original.md:1`](../../README.original.md#L1)
