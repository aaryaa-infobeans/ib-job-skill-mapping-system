#!/usr/bin/env python3
"""Generate a valid JWT token for testing the API."""

import jwt
from datetime import datetime, timedelta, timezone

# Load the secret from .env (should match your JWT_SECRET_KEY)
SECRET_KEY = "test-secret-key-for-testing"
ALGORITHM = "HS256"

# Create token payload
payload = {
    "sub": "test-client",
    "client_id": "test-client",
    "exp": datetime.now(timezone.utc) + timedelta(days=365)
}

# Generate token
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

print("=" * 80)
print("JWT TOKEN GENERATED")
print("=" * 80)
print("\nYour JWT Token (copy this):")
print("-" * 80)
print(token)
print("-" * 80)

print("\n📋 Copy and use this token in:")
print("   • Swagger UI: Click 'Authorize' button, paste token")
print("   • curl: -H 'Authorization: Bearer <token>'")
print("   • Postman: Authorization > Bearer Token")

print("\n✅ This token is valid for 365 days")
print("=" * 80)
