# Reconciliation — ARCHITECTURE.md

- **Input:** `docs/ARCHITECTURE.md`
- **Gaps addressed:** preserved the local SQLite/simulated-permission boundary and the future API,
  DynamoDB, AgentCore, and IAM path; the UI requirements do not claim those future components exist.
- **Residual:** the later hosted backoffice still needs authentication, authorization, and approval
  ownership decisions.
