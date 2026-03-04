# Active Work: llms.txt + Rate Limiting

**Claimed**: 2026-03-04 12:10
**Session**: Claude Opus (category-fix session, continued)
**Branch**: feat/llms-txt-rate-limiting

## Scope

### llms.txt
- New route in `web_routes.py` serving `/llms.txt` and `/llms-full.txt`
- Content describes Assay for AI agents (what it does, API endpoints, MCP server)

### Rate Limiting
- Add `slowapi` dependency
- Middleware in `app.py` for global rate limiting
- 100 requests/day default on `/v1/*` API endpoints
- No rate limit on web pages (HTML routes)

## Files I'll Touch
- `src/assay/api/app.py` — rate limit middleware setup
- `src/assay/api/routes.py` — rate limit decorators on API endpoints
- `src/assay/api/web_routes.py` — new llms.txt route (plain text, not HTML)
- `pyproject.toml` — add slowapi dependency
- `src/assay/templates/` — NOT touching templates
- `reports/` — NOT touching reports
