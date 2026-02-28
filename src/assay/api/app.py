"""Main FastAPI application for Assay."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import router
from .web_routes import router as web_router

app = FastAPI(
    title="Assay",
    description="The quality layer for agentic software — package agent-friendliness ratings",
    version="0.1.0",
)

# CORS — allow all origins for MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)

# Web frontend routes
app.include_router(web_router)

# Static files and templates for web frontend
_src_dir = Path(__file__).parent.parent  # src/assay/
_templates_dir = _src_dir / "templates"
_static_dir = _src_dir / "static"

if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Jinja2 templates — available for web frontend routes
templates = Jinja2Templates(directory=str(_templates_dir))
