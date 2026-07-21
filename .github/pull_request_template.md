## Story

- Story: `<!-- e.g. 1-1-version-the-bench-schema... -->`
- Related issue: `<!-- Refs #123 -->`
- Target branch: `feature/bench`

## User story

<!-- Copy the complete user story statement from the story artifact. -->

## Acceptance criteria

<!-- Copy every acceptance criterion from the corresponding story artifact. Do not summarize or omit criteria. -->

- [ ] AC1:
- [ ] AC2:
- [ ] AC3:

## Implementation summary

<!-- Describe what was implemented and how it satisfies the acceptance criteria. -->

## Files changed

<!-- List the important files and why they changed. -->

- `path/to/file.py` — reason
- `path/to/test_file.py` — reason

## Testing

### Automated tests

```text
# Command:
uv run pytest

# Result:
<!-- Paste the actual result, for example: 24 passed, 2 skipped -->
```

- [ ] Tests pass locally.
- [ ] New or changed behavior has automated coverage.
- [ ] No test result was inferred or omitted.

### Manual verification

<!-- Include concrete steps for UI, accessibility, responsive, migration, or other behavior that cannot be fully covered automatically. -->

1.
2.
3.

## Contract and regression checks

- [ ] Canonical SPEC decisions are preserved.
- [ ] SQLite remains authoritative for Bench state.
- [ ] Shared behavior remains behind the appropriate domain/tool seam.
- [ ] Existing behavior remains intact.
- [ ] No hosted authentication, real provisioning, AWS deployment, or unrelated scope was introduced.

## Review notes

### Known limitations

<!-- State any limitations explicitly. Use "None" when applicable. -->

### Follow-up work

<!-- Link later stories or issues when applicable. Use "None" when applicable. -->

## Review checklist

- [ ] Acceptance criteria are fully satisfied.
- [ ] Code review completed.
- [ ] Test output is included.
- [ ] Documentation/artifacts are updated where required.
- [ ] This PR is ready to merge into `feature/bench`.
