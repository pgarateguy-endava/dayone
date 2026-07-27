"""Document storage for EOD reports and Endava Profile PDFs.

AWS integration (from local): when BENCH_DOCS_S3_BUCKET is set, documents live in S3;
otherwise they stay on local disk (`.local-progress/`). Same functions either way, so the
callers (`eod_report.save_eod_report`, the onboarding PDF upload) don't change.
"""
from __future__ import annotations

from pathlib import Path

from bench.config import REPORTS_DIR, PROGRESS_DIR, aws_region, docs_s3_bucket


def _s3_client():
    import boto3

    return boto3.client("s3", region_name=aws_region())


def put_report(filename: str, content: str) -> str:
    """Store an EOD report. Returns a local path or an s3:// URI."""
    bucket = docs_s3_bucket()
    if bucket:
        key = f"reports/{filename}"
        _s3_client().put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"),
                                ContentType="text/markdown")
        return f"s3://{bucket}/{key}"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(REPORTS_DIR) / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def put_profile_pdf(employee_email: str, data: bytes, filename: str) -> str:
    """Store an uploaded Endava Profile PDF. Returns a local path or an s3:// URI."""
    safe = employee_email.replace("@", "_at_")
    bucket = docs_s3_bucket()
    if bucket:
        key = f"profiles/{safe}/{filename}"
        _s3_client().put_object(Bucket=bucket, Key=key, Body=data,
                                ContentType="application/pdf")
        return f"s3://{bucket}/{key}"
    profiles_dir = PROGRESS_DIR / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    path = profiles_dir / f"{safe}_{filename}"
    path.write_bytes(data)
    return str(path)
