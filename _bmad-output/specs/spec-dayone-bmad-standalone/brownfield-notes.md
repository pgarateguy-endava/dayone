# Brownfield notes

The hub currently owns the BMad runtime integration under `_bmad/`, while the DayOne child owns source code, `docs/`, and `_bmad-output/` artifacts. BMad skills resolve `{project-root}/_bmad/...`, so direct execution from the child currently lacks the expected project-local configuration and resolver scripts.

The child already contains planning artifacts, implementation stories, sprint status, architecture/UX/spec documents, and development workflow instructions. The future bootstrap must preserve those locations and make their ownership explicit rather than creating a second planning tree.

The child repository has its own `feature/bench` principal branch and requires dedicated story worktrees. The setup must be performed against the latest post–Story 1.3 `feature/bench` state and must remain limited to this child repository.

The current environment provides BMad skill definitions outside the repository. The spec therefore separates those environment-installed skills from committed child-local BMad configuration and durable artifacts. Contributors install the supported skill/plugin package separately; the child does not vendor the hub's `.agents/` tree or depend on the hub at runtime.

The existing README is currently the repository's onboarding entry point. Once the standalone BMad integration is complete, it must be preserved under a renamed filename and replaced by a generated full README based on `docs/BENCH_SPEC.md`. The generated README owns navigation and setup guidance; the Bench PRD and other canonical documents remain the source of product and architecture requirements.
