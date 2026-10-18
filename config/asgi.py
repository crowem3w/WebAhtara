"""Run with: uvicorn api.main:app  (FastAPI serves /v1 and /docs, Django serves /admin)."""
from api.main import app  # noqa: F401
