# Blind Hunter review prompt

Invoke the `bmad-review-adversarial-general` skill on the implementation diff
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

The intentional `README.md` deletion and preserved `README.original.md` are
in scope. Do not recommend generating the replacement README in this review;
that is explicitly post-bootstrap. Report only actionable findings with file
and line references, severity omitted, and distinguish current-change defects
from pre-existing baseline issues.
