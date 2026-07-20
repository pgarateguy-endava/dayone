# Architecture spine review — adversarial seam lens

Verdict: no unresolved pair of independently built UI units can safely own the same domain mutation
once AD-5, AD-9, AD-10, and AD-15 are followed; five explicit decisions remain the seams to close.

- A web route and an API route cannot diverge on business behavior because both call `bench/tools`.
- A task editor and person-progress editor cannot overwrite the same semantic state because AD-3
  separates catalog templates from person instances.
- A report page and Teams notifier cannot disagree about delivery if both consume the report/
  notification status projections in AD-10.
- Archive and date-status views cannot erase history or confuse lifecycle because AD-8 separates them.
- Fragment and full-page mutations have distinct, enforceable response contracts in AD-11.

Potential holes are surfaced rather than guessed: task deletion versus historical identity, responsible
uniqueness, simulated approval states, and actor provisioning are all open decisions in the spine.
