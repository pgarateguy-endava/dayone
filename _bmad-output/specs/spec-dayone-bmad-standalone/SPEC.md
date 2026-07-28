---
id: SPEC-dayone-bmad-standalone
companions:
  - implementation-prompt.md
  - brownfield-notes.md
sources:
  - ../../../AGENTS.md
  - ../../../docs/development-workflow.md
  - ../../../docs/BENCH_SPEC.md
---

# DayOne child-local BMad workflow

## Why

The DayOne child repository must be an independent BMad project root so its workflows can run from the child directory and its planning, implementation, configuration, and memory artifacts remain versioned with the project. Contributors may install the BMad skill/plugin distribution separately in their environment, but DayOne must provide all project-owned integration and durable artifacts required after that prerequisite is installed. The setup is applied only after Story 1.3 has been developed and merged; `feature/bench` is the principal baseline to inspect.

## Capabilities

### CAP-1 — Resolve BMad from the child root

- **intent:** Run BMad workflows with `projects/dayone` as `{project-root}`.
- **success:** From the child directory, configuration and customization resolvers load child-local `_bmad/` files without reaching into the hub repository.

### CAP-2 — Preserve team workflow contract

- **intent:** Keep DayOne-specific BMad rules, agents, customizations, and workflow settings available to every contributor.
- **success:** A fresh checkout contains the committed child-local team configuration and resolves project name, languages, artifact paths, workflow rules, and agent settings consistently.

### CAP-3 — Preserve durable artifacts

- **intent:** Keep all BMad outputs and load-bearing workflow memory with the child project.
- **success:** Planning artifacts, sprint status, story files, specs, project context, and relevant `.memlog.md` files are discoverable under the child repository and are not dependent on hub-local paths.

### CAP-4 — Support the full BMad lifecycle

- **intent:** Use analysis, planning, solutioning, implementation, review, QA, and retrospective workflows directly against DayOne.
- **success:** The child-local setup supports the installed BMad menu and resolves the required inputs/outputs for PRD, UX, architecture, epics/stories, readiness, sprint planning, story creation/validation, development, review, QA, and retrospective workflows.

### CAP-5 — Make the setup reproducible and safe

- **intent:** Let another contributor reproduce the setup from a clean clone after installing the supported BMad skill/plugin prerequisite.
- **success:** A documented installation and validation procedure distinguishes committed team files from gitignored personal files, uses the child as the only project root, and never includes tokens, `.env` files, absolute hub paths, or hub repository state.

### CAP-6 — Generate the post-bootstrap README

- **intent:** Give contributors one complete entry point for the Bench project and its child-local BMad workflow after the standalone setup is complete.
- **success:** After the standalone BMad tasks are finished, the original README is preserved under a renamed filename and a new complete `README.md` is generated from the canonical Bench PRD at `docs/BENCH_SPEC.md`, incorporating the implemented project structure, setup, validation, development workflow, and safety rules without deleting or editing the preserved original directly.

## Constraints

- Execute after Story 1.3 is merged. Begin by inspecting the latest `feature/bench` code and history; do not rely on the pre-merge Story 1.3 worktree.
- The child project is the authoritative project root for BMad paths: `_bmad/`, `_bmad-output/`, `docs/`, source, and tests resolve relative to `projects/dayone`.
- Team-owned BMad runtime integration, configuration, customizations, manifests, scripts, and artifacts required for direct execution must be committed to the child repository. Personal `config.user.*` files remain gitignored.
- Environment-installed skill definitions are a documented prerequisite and remain separate from project-owned configuration. Do not vendor the hub's `.agents/` tree or make the hub repository a source of runtime files.
- Preserve the child `AGENTS.md`, `docs/development-workflow.md`, feature branch/worktree conventions, SQLite authority, and current product behavior.
- Do not modify product code, Story 1.3 implementation, DynamoDB behavior, or requirements merely to bootstrap BMad. Any setup change that affects those areas is out of scope.
- Do not commit credentials, tokens, `.env` files, generated virtual environments, caches, or personal BMad settings.
- The setup must not make the hub repository a runtime dependency when invoked from the child.
- README generation is a post-bootstrap deliverable. The existing README is renamed and preserved before the new README is created; it is not edited in place.
- The canonical product source for the new README is `docs/BENCH_SPEC.md`; the generated README may also link to the existing architecture, UX, workflow, and BMad artifacts rather than duplicating them.

## Non-goals

- Implementing or reviewing Story 1.3.
- Synchronizing the DynamoDB schema or behavior with SQLite; that remains a separate follow-up epic/story.
- Replacing the installed BMad skills/plugin distribution or inventing a new workflow engine.
- Moving existing project requirements, UX, architecture, or story content into duplicate copies without a clear ownership rule.
- Committing personal identity, credentials, local paths, AWS configuration, `.env` content, or generated caches.

## Success signal

After Story 1.3 is merged into `feature/bench`, a clean child checkout can run BMad from `projects/dayone`, resolve all required configuration and customizations locally, create/validate/update a story, read and update sprint status, and preserve the resulting artifacts under the child repository without hub-local path dependencies or product-code changes.

After the standalone tasks are complete, the same checkout also contains a generated full README that explains the Bench product, local setup, BMad prerequisite, validation commands, repository workflow, and safety boundaries, while the original README remains recoverable under its renamed filename.

## Assumptions

- Contributors install the supported BMad skill/plugin definitions separately; this change makes the project integration and artifact contract child-local.
- The existing DayOne `_bmad-output` planning and implementation artifacts remain the source of truth and are migrated/normalized in place rather than duplicated.
- The future execution will use a dedicated branch/worktree based on the then-current `feature/bench`.

## Resolved Decisions

- **Skill installation:** Contributors install the supported BMad skill/plugin package separately, following the DayOne README. The repository does not vendor skill definitions.
- **Project integration:** The repository commits the minimum child-local `_bmad/` configuration, metadata, manifests, resolver/memory scripts, committed team customizations, and all durable `_bmad-output/` artifacts required by the workflows.
- **Runtime boundary:** BMad is invoked with the DayOne directory as `{project-root}`. Skill definitions may live elsewhere in the environment, but no resolver or workflow may depend on `/home/.../ai-playground` or another hub-local path.
- **Version compatibility:** The README documents the supported BMad version/plugin prerequisite and the validation command that accepts the installed skill path. Updating that prerequisite is a deliberate project change.
