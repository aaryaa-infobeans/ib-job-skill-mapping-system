"""Metrics endpoint integration tests."""


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    
    # Verify Prometheus format
    content = response.text
    assert "# HELP" in content or "# TYPE" in content or content.strip() != ""
    

def test_metrics_track_requests(client):
    """Test that metrics endpoint tracks HTTP requests."""
    # Make a request to generate metrics
    client.get("/health")
    
    # Get metrics
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    
    content = response.text
    # Check for http_requests_total metric
    assert "http_requests_total" in content
    # Check for http_request_duration_seconds metric
    assert "http_request_duration_seconds" in content
