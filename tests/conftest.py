"""Test configuration and fixtures."""

import pytest
import sqlalchemy.pool
import time
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Import all models to ensure they are registered with Base.metadata
from app.db.models import models as _  # noqa: F401

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=sqlalchemy.pool.StaticPool,  # Share same connection for in-memory DB
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_test_token(client_id: str = "test-client"):
    """Create a test JWT token."""
    payload = {
        "sub": client_id,
        "client_id": client_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    # Use any secret key - dev mode doesn't validate signature
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def db():
    """Database fixture that creates tables before each test."""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Test client fixture with database override and auth token."""
    app.dependency_overrides[get_db] = override_get_db
    try:
        test_client = TestClient(app)
        # Add default auth token to all requests
        token = create_test_token()
        test_client.headers = {**test_client.headers, "Authorization": f"Bearer {token}"}
        yield test_client
    finally:
        app.dependency_overrides.clear()
