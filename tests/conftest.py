"""Test isolation from the developer's local .env.

`bench/config.py` loads the repo-root `.env` on import, which on a dev machine may set
`BENCH_STORAGE=dynamodb`, `AWS_PROFILE`, `BENCH_DOCS_S3_BUCKET`, etc. Tests must be
deterministic regardless of that, so this autouse fixture forces the local defaults
(SQLite storage, no S3, fake AWS creds). Tests that exercise AWS paths opt in explicitly
by setting the relevant env vars themselves (see test_dynamo.py / test_docstore.py).
"""
import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "1")
    monkeypatch.setenv("BENCH_STORAGE", "sqlite")
    monkeypatch.delenv("BENCH_DOCS_S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
