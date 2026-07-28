# Child-local BMad workflow

DayOne is the BMad project root for this repository. The project-owned `_bmad/`
directory contains team configuration, resolver scripts, manifests, and durable
workflow boundaries. The BMad skill definitions are an environment-installed
prerequisite and are not vendored into this repository.

## Prerequisite

Install the supported BMad Method skill/plugin distribution separately in your
Codex or compatible agent environment, using the environment's normal installer
for version 6.10.0 or a compatible release. The project integration is aligned
with the metadata recorded in `_bmad/_config/manifest.yaml`; personal installer
configuration must remain outside version control.

## Run from the child root

```bash
cd projects/dayone
python3 _bmad/scripts/resolve_config.py --project-root "$PWD"
python3 _bmad/scripts/resolve_customization.py \
  --skill <installed-skill-path> --key workflow
```

The resolved planning, implementation, knowledge, and output paths must stay
inside the child repository. Use `uv run pytest` for project validation. BMad
outputs belong under `_bmad-output/`; existing planning artifacts, stories,
sprint status, specs, and memory logs remain the durable source of truth.

Do not copy the hub `.agents/` tree, use hub-local paths at runtime, commit
`.env` files or credentials, or add personal `_bmad` configuration. README
replacement remains a post-bootstrap deliverable based on `docs/BENCH_SPEC.md`.
