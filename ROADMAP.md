# Assay Roadmap

Future enhancements beyond MVP. See GOAL.md for MVP success criteria.

---

## Data Quality & Freshness

- **Display last-evaluated date per package** — surface `last_evaluated` in API responses, MCP results, and website detail pages so consumers know how stale a rating might be
- **Automated re-evaluation pipeline** — scheduled re-evaluation of packages whose `last_evaluated` exceeds a staleness threshold (e.g., 90 days)
- **Score history / trend tracking** — track AF/Security/Reliability scores over time, detect regressions
- **Evaluation confidence indicator** — distinguish between hand-curated evaluations (Opus, in-session) vs batch-generated (Haiku, automated)

## Evaluation Pipeline

- **Backfill security/reliability sub-components** — the 500+ existing evaluations use old schema with only top-level security_score and no reliability_score; batch re-evaluate to populate all 14 sub-components
- **Live API testing** — actually call package APIs (where free tier allows) to verify error formats, latency, auth flows
- **Community-submitted evaluations** — allow package maintainers to submit/correct evaluation data
- **Multi-source context gathering** — beyond GitHub README: npm/PyPI metadata, changelog parsing, status page scraping

## API & MCP Server

- **Comparison endpoint** — `GET /v1/compare?ids=a,b,c` to compare packages side-by-side
- **Change feed** — `GET /v1/packages/updated-since?timestamp=...` for consumers tracking updates
- **Filter by score dimension** — query packages by security >= X, reliability >= Y
- **Category leaderboards** — best-in-category rankings across all three dimensions

## Website

- **Score breakdown visualization** — radar/spider charts showing AF/Security/Reliability sub-components
- **Staleness badge** — visual indicator when a package hasn't been re-evaluated recently
- **Category browse pages** — organized listings by category with sort/filter
- **Package comparison page** — side-by-side comparison of 2-3 packages

## CLI

- **`assay check <package>`** — quick terminal lookup of scores
- **`assay compare <a> <b>`** — terminal comparison
- **`assay stale --days 90`** — list packages needing re-evaluation

## Infrastructure

- **OpenAPI spec auto-published** — generated from FastAPI, hosted at /openapi.json
- **llms.txt** — machine-readable site description at assay.tools/llms.txt
- **CI/CD pipeline** — automated testing and deployment
- **Rate limiting on public API** — protect production DB from abuse
