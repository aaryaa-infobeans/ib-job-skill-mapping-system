#!/bin/bash
# Smoke test script

echo "Running smoke tests..."

# Check if API is responding
curl -f http://localhost:8000/health || exit 1

echo "Smoke tests passed!"
