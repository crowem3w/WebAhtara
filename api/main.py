"""
ASGI entrypoint:  uvicorn api.main:app

FastAPI serves the public API (/v1/..., /docs). Anything FastAPI doesn't match falls through to Django,
which serves /admin/ and its static files.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

django_app = get_asgi_application()  # also runs django.setup(); must happen before importing models

from django.conf import settings  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from .routes import router  # noqa: E402

app = FastAPI(title="Ahtara listings API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["Content-Type"]
)
app.include_router(router, prefix="/v1")
app.mount("/", django_app)  # keep last
