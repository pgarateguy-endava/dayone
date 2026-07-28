# Implementation prompt: make DayOne BMad child-local

Execute this prompt only after Story 1.3 has been developed, reviewed, merged, and is present on the latest `feature/bench` branch. The result must work from a clean DayOne clone after the contributor installs the supported BMad skill/plugin prerequisite; the hub repository must not be needed at runtime.

## Role

Act as a repository-integration engineer. Make `projects/dayone` a self-contained BMad project root for project configuration and durable artifacts. Do not implement product functionality.

## Required starting checks

1. Work from a dedicated worktree and branch created from the latest `feature/bench`.
2. Read the hub `AGENTS.md`, child `AGENTS.md`, and `docs/development-workflow.md`.
3. Verify Story 1.3 is merged and inspect the current `feature/bench` tree, recent commits, remotes, and branch configuration.
4. Inventory the hub BMad installation and the child’s existing `_bmad-output` artifacts. Identify which files are project integration, which are durable generated artifacts, and which are personal or environment-owned. Use the hub inventory as a migration source only; do not leave the hub as a runtime dependency.
5. Do not overwrite unrelated child changes.

## Implementation requirements

1. Add the minimum child-local `_bmad/` structure required by the installed workflows: configuration, module/core metadata, resolver/memory scripts, manifests, and committed team customizations. Do not copy personal configuration or the full `.agents/` skill distribution.
2. Configure `{project-root}`-relative paths for the child project name, communication/document languages, planning artifacts, implementation artifacts, project knowledge, and output folder.
3. Preserve existing `_bmad-output/planning-artifacts/` and `_bmad-output/implementation-artifacts/` content. Bring the post–Story 1.3 story artifact and sprint status into the child-owned history when the merge makes them available.
4. Preserve project memory logs and project context where downstream skills require them. Do not duplicate adopted UX, architecture, or product documents; reference their existing child paths.
5. Carry the DayOne team rules into child-local custom configuration, including `docs/development-workflow.md`, `uv run pytest`, feature/bench workflow, SQLite authority, exclusive backend-source intent, and credential safety.
6. Keep personal configuration files gitignored and ensure `.gitignore` excludes `.env`, `.venv`, caches, personal config, and local runtime data.
7. Add or update a concise child-local README section documenting the supported BMad installation prerequisite, how to invoke BMad from the child root, how to provide the installed skill path, and how to validate resolution.
8. Do not vendor `.agents/` or unrelated hub repository files unless the implementation proves they are required for a clean child execution and the ownership/license decision is explicit.
9. After the standalone BMad integration tasks are complete, rename the existing `README.md` to a recoverable filename such as `README.original.md`; do not edit that preserved file in place. Generate a new complete `README.md` from the canonical Bench PRD at `docs/BENCH_SPEC.md`, incorporating the final child-local BMad setup, repository structure, local development commands, validation steps, story/worktree workflow, and security boundaries.

## Backend boundary

The BMad bootstrap must not change application storage behavior. SQLite and DynamoDB remain separate product concerns. Do not use this task to synchronize their schemas or create a hybrid runtime; DynamoDB parity remains a later epic/story.

## Validation

From the child project root, verify:

```bash
python3 _bmad/scripts/resolve_config.py --project-root "$PWD"
python3 _bmad/scripts/resolve_customization.py --skill <installed-skill-path> --key workflow
uv run pytest
```

Also verify that:

- resolved paths point inside the child repository;
- a contributor can install the documented BMad prerequisite and a story workflow can then read the child epics and sprint status;
- a spec workflow writes under `_bmad-output/specs/`;
- no resolver output references `/home/.../ai-playground/_bmad` or another hub-local path;
- `git status` contains no credentials, `.env`, virtual environment, cache, or personal config files;
- the final diff contains only child-repository integration/configuration/artifact changes;
- the README's documented installation and validation procedure works without copying files from the hub repository.
- the original README is preserved under the documented renamed filename;
- the new README is based on `docs/BENCH_SPEC.md`, accurately describes the implemented standalone setup, and links to authoritative project documents instead of inventing conflicting requirements.

## Deliverables

- Child-local BMad project/configuration integration, with skills installed separately as a documented prerequisite.
- Preserved and discoverable BMad artifacts.
- README/bootstrap instructions.
- A generated full `README.md` based on `docs/BENCH_SPEC.md`, plus the preserved renamed original README.
- Validation evidence and the documented external skill-install prerequisite, including the supported version/plugin name.

## Stop conditions

Stop and report instead of guessing if Story 1.3 is not merged, the latest `feature/bench` cannot be identified, required BMad project files have incompatible licenses, the supported skill/plugin prerequisite cannot be documented, or the setup would require changing product behavior or committing personal state.
