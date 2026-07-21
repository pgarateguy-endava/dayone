import pytest

import bench.config as config
import bench.docstore as docstore


def test_reports_and_pdfs_go_to_local_disk_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(config, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(docstore, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(docstore, "PROGRESS_DIR", tmp_path)
    monkeypatch.delenv("BENCH_DOCS_S3_BUCKET", raising=False)

    report_uri = docstore.put_report("2026-07-20_ada.md", "# report")
    pdf_uri = docstore.put_profile_pdf("ada@test.com", b"%PDF-1.4", "cv.pdf")
    assert report_uri.endswith("2026-07-20_ada.md") and not report_uri.startswith("s3://")
    assert pdf_uri.endswith("cv.pdf") and not pdf_uri.startswith("s3://")


def test_reports_and_pdfs_go_to_s3_when_bucket_set(monkeypatch):
    moto = pytest.importorskip("moto")
    import boto3

    monkeypatch.setenv("BENCH_DOCS_S3_BUCKET", "bench-docs-test")
    monkeypatch.delenv("AWS_PROFILE", raising=False)  # use moto's fake creds, not the .env SSO profile
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")

    with moto.mock_aws():
        boto3.client("s3", region_name="us-west-2").create_bucket(
            Bucket="bench-docs-test",
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

        report_uri = docstore.put_report("2026-07-20_ada.md", "# report")
        pdf_uri = docstore.put_profile_pdf("ada@test.com", b"%PDF-1.4", "cv.pdf")
        assert report_uri == "s3://bench-docs-test/reports/2026-07-20_ada.md"
        assert pdf_uri == "s3://bench-docs-test/profiles/ada_at_test.com/cv.pdf"

        # content actually landed in S3
        s3 = boto3.client("s3", region_name="us-west-2")
        body = s3.get_object(Bucket="bench-docs-test",
                             Key="reports/2026-07-20_ada.md")["Body"].read()
        assert body == b"# report"
