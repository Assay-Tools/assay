"""Entry point: run with `uv run python -m assay`."""

import uvicorn

from assay.config import settings
from assay.database import init_db

init_db()
uvicorn.run("assay.api.app:app", host=settings.api_host, port=settings.api_port, reload=True)
