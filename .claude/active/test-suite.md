# Active Work: Initial Test Suite

**Claimed**: 2026-03-04 12:02
**Session**: Claude Opus (report-building session, continued)
**Branch**: main (new files only, no conflicts)

## Scope

Create initial pytest suite covering:
- Models (Package, Category, relationships)
- API routes (packages, categories, compare, stats, queue)
- MCP server tools (find_packages, get_package, etc.)

## Files I'll Touch
- `tests/` — NEW directory, all new files
- `pyproject.toml` — add pytest/httpx dev dependencies
- `conftest.py` or `tests/conftest.py` — fixtures

## Non-Overlapping
- NOT touching `src/assay/api/routes.py` (rate-limit session owns that)
- NOT touching `src/assay/api/web_routes.py`
- NOT touching `src/assay/api/app.py`
- Read-only access to models and existing code for test writing
