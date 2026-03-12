#!/usr/bin/env bash
# Run the backend from project root so the `backend` module is found.
# Loads backend/.env; when PERSISTENCE_BACKEND=gcp, GOOGLE_APPLICATION_CREDENTIALS
# is set automatically to the service account JSON in backend/ (see app/config.py).
set -e
cd "$(dirname "$0")/.."
exec .venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
