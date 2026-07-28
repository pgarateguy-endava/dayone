# Edge Case Hunter review prompt

Invoke the `bmad-review-edge-case-hunter` skill on the implementation diff
for the approved standalone-BMad spec.

Review baseline: `37a8abc333dfb225be0d9806229dd260d7f081c0`.

Inspect all tracked changes with:

```bash
git diff 37a8abc333dfb225be0d9806229dd260d7f081c0 --
```

Also inspect every untracked path because the diff command does not include
them:

```text
.gitignore
_bmad/config.toml
_bmad/bmm/config.yaml
_bmad/core/config.yaml
_bmad/custom/bmad-quick-dev.toml
_bmad/_config/manifest.yaml
_bmad/scripts/resolve_config.py
_bmad/scripts/resolve_customization.py
_bmad/scripts/memlog.py
docs/bmad-workflow.md
_bmad-output/implementation-artifacts/spec-dayone-bmad-standalone.md
_bmad-output/specs/spec-dayone-bmad-standalone/*
README.original.md
```

Walk every branching path and boundary condition: fresh clone, missing skill,
missing personal config, hub path leakage, malformed TOML, non-child working
directory, ignored secrets/caches, existing memory logs, and README sequencing.
Report only unhandled edge cases with file and line references. Do not suggest
implementing the replacement README or changing Bench product behavior.
