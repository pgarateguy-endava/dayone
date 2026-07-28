## Deferred from: code review of 1-3-audit-shared-mutations-atomically-and-expose-action-history-queries (2026-07-27)

- Complete DynamoDB backend exclusivity and audit/history parity. The current selector still routes notification/conversation data to DynamoDB while people, catalog, and audit history remain in SQLite. This is pre-existing transitional behavior explicitly deferred by Story 1.3 and must be resolved before DynamoDB-only mode is enabled. See `bench/config.py`, `bench/notify.py`, and `bench/tools/audit.py`.

## Deferred from: code review second pass (2026-07-27)

- DynamoDB date/notification atomicity remains deferred with full backend parity. In the current transitional mode, `set_bench_start_date()` updates SQLite person/audit state before clearing DynamoDB notifications. See `bench/tools/state.py`.
