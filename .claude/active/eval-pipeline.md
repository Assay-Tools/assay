# Active Work: Evaluation Pipeline + CLI

**Claimed**: 2026-03-04
**Session**: Claude Opus (full workboard sweep)
**Branch**: main

## Scope
- Submission API — POST /v1/evaluations
- Auth for submissions — X-API-Key header
- Evaluation review queue — pending/approved status
- Evaluation skill — portable Claude Code slash command
- CLI tool — assay check/compare/stale

## Files I'll Touch
- `src/assay/api/auth.py` — new auth dependency
- `src/assay/api/routes.py` — submission endpoint
- `src/assay/api/schemas.py` — submission response model
- `src/assay/models/package.py` — submission status field if needed
- `tests/test_api_submissions.py` — new test file
- CLI and skill files TBD
