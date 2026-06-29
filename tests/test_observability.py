import pytest
import logging
from fastapi.testclient import TestClient
from api.main import app
from api.observability import requests_total

client = TestClient(app)

def test_request_id_header_present():
    """Asserts that X-Request-ID response header is set and non-empty."""
    response = client.get("/readyz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != ""

def test_requests_total_incremented():
    """Asserts that requests_total baseline increments reliably following requests."""
    try:
        initial_count = requests_total.labels(path="/readyz", status="200")._value.get()
    except Exception:
        initial_count = 0

    response = client.get("/readyz")
    assert response.status_code == 200

    updated_count = requests_total.labels(path="/readyz", status="200")._value.get()
    assert updated_count == initial_count + 1

def test_structured_log_matches_header(caplog):
    """Asserts that captured log output shares identical request tracking IDs."""
    with caplog.at_level(logging.INFO, logger="m11.api"):
        response = client.get("/readyz")
        assert response.status_code == 200
        header_id = response.headers["X-Request-ID"]
        
        # Verify targeted request tracking string signature inside captured log scopes
        id_found_in_logs = False
        for record in caplog.records:
            if header_id in record.message:
                id_found_in_logs = True
                break
                
        assert id_found_in_logs, f"Could not find matching log line containing request ID: {header_id}"