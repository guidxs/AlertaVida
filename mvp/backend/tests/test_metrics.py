import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

os.environ.setdefault("DATABRICKS_SERVER_HOSTNAME", "metrics-test.invalid")
os.environ.setdefault("DATABRICKS_HTTP_PATH", "/sql/metrics-test")
os.environ.setdefault("DATABRICKS_TOKEN", "metrics-test-placeholder")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app


def test_metrics_endpoint_reports_http_requests_without_counting_scrapes() -> None:
    with TestClient(app) as client:
        response = client.get("/api/live?token=synthetic-test-value")
        assert response.status_code == 200
        not_found = client.get("/not-a-real-route")
        assert not_found.status_code == 404

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "text/plain" in metrics_response.headers["content-type"]

    metric_families = list(text_string_to_metric_families(metrics_response.text))
    samples = [sample for family in metric_families for sample in family.samples]

    live_requests = [
        sample
        for sample in samples
        if sample.name == "http_requests_total"
        and sample.labels.get("handler") == "/api/live"
        and sample.labels.get("method") == "GET"
        and sample.labels.get("status") == "2xx"
    ]
    assert len(live_requests) == 1
    assert live_requests[0].value == 1

    not_found_requests = [
        sample
        for sample in samples
        if sample.name == "http_requests_total"
        and sample.labels.get("handler") == "none"
        and sample.labels.get("method") == "GET"
        and sample.labels.get("status") == "4xx"
    ]
    assert len(not_found_requests) == 1
    assert not_found_requests[0].value == 1

    assert not any(
        sample.name == "http_requests_total"
        and sample.labels.get("handler") == "/metrics"
        for sample in samples
    )
    assert any(family.name == "http_request_duration_seconds" for family in metric_families)
    assert any(family.name == "http_requests_inprogress" for family in metric_families)
    assert "synthetic-test-value" not in metrics_response.text


def test_rpa_summary_endpoint_exposes_latest_output() -> None:
    with TestClient(app) as client:
        response = client.get("/api/rpa/ultima-execucao")
    assert response.status_code == 200
    assert "execution_id" in response.json()
    assert "total_processados" in response.json()
