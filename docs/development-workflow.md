# Development Workflow

## Story branches and worktrees

All story development starts from `feature/bench`.

Create one branch and worktree per story:

```bash
git worktree add ../worktrees/dayone/<story-key> \
  -b feat/bench-<story-key> feature/bench
```

Do not implement stories directly on `feature/bench`, the default branch, or another story worktree.

The BMad story artifact and
`_bmad-output/implementation-artifacts/sprint-status.yaml` are the workflow source of truth.

## Story lifecycle

For each story:

1. Create or load the story artifact.
2. Validate the story.
3. Implement it in its dedicated worktree.
4. Run `uv run pytest`.
5. Run code review.
6. Create a draft PR targeting `feature/bench`.

```bash
gh pr create --draft \
  --base feature/bench \
  --head <story-branch>
```

## Pull requests

Every story PR uses `.github/pull_request_template.md`.

The PR must include:

- The complete acceptance criteria from the story artifact.
- Implementation summary and changed files.
- Actual test commands and results.
- Manual verification steps where applicable.
- Known limitations and follow-up work.
- Related GitHub Issue, if one exists.

Use `Refs #<issue-number>` for draft PRs and `Closes #<issue-number>` only when ready to merge.

## Worktree cleanup

After a story PR is merged:

```bash
git worktree remove ../worktrees/dayone/<story-key>
git worktree prune
```

Delete the local story branch after confirming it is merged:

```bash
git branch -d feat/bench-<story-key>
```

## Scope and safety

- Do not modify more than one child repository unless explicitly required.
- Do not modify requirements, UX, architecture, ADR, or test documents without authorization.
- Preserve the canonical SPEC decisions and six-step foundation sequence.
- Keep Bench isolated as a parallel domain with SQLite as its local source of truth.
