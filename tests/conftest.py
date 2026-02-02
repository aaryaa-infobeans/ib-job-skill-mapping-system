"""Test configuration and fixtures."""
import pytest


@pytest.fixture
def client():
    """Test client fixture."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
