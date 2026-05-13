"""ASGI entry point.

Run locally with:

    uvicorn src.api.main:app --reload
"""

from .app import create_app

app = create_app()
