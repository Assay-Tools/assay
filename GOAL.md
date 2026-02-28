# Assay — MVP Goal & Success Criteria

**Domain**: assay.tools
**Tagline**: The quality layer for agentic software.

---

## Refined Goal

Build a complete, locally-running MVP of Assay: a platform that rates software packages on agent-friendliness, served via REST API, MCP server, and website. The evaluation pipeline is itself agentic — agents discover, test, and score packages autonomously.

The MVP proves three things:
1. **The data is valuable** — structured ratings that agents can query to select tools
2. **The pipeline is agentic** — agents can autonomously evaluate packages
3. **The product works end-to-end** — discovery → evaluation → database → API/MCP/website

---

## Success Criteria

### Must Have (MVP is not done without these)
- [ ] Database schema implemented with full package record structure
- [ ] 200+ MCP servers rated with structured data (AF Score + key schema fields)
- [ ] REST API with filter/search/detail endpoints, serving pre-computed data
- [ ] Assay's own MCP server (dogfooding — agents can call `find_packages`, `get_package`)
- [ ] Basic web frontend: browse categories, search, view package detail pages
- [ ] Evaluation pipeline that can rate a new package given a URL/name
- [ ] Everything runs locally with `docker compose up` or equivalent single command
- [ ] Deploy-ready configuration for Railway or Fly.io

### Should Have
- [ ] Comparison endpoint (`/v1/compare?ids=a,b,c`)
- [ ] Change feed endpoint (`/v1/packages/updated-since?timestamp=...`)
- [ ] `best_when` / `avoid_when` fields populated for all rated packages
- [ ] `known_agent_gotchas` populated where relevant
- [ ] CLI tool: `assay check <package-name>` for quick terminal lookups

### Nice to Have
- [ ] Automated re-evaluation pipeline (scheduled, not manual)
- [ ] Score history / trend tracking
- [ ] OpenAPI spec auto-generated and published
- [ ] llms.txt at assay.tools/llms.txt

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 WRITE SIDE (Agentic)             │
│                                                  │
│  Discovery Agent ─→ finds packages from          │
│                     MCP directories, GitHub       │
│                                                  │
│  Evaluation Agent ─→ reads docs, analyzes code,  │
│                      tests APIs, fills schema     │
│                                                  │
│  Scorer Agent ─→ computes AF score from           │
│                  evaluation data                  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │              PostgreSQL / SQLite            │  │
│  │         (structured package records)        │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
├─────────────────────────────────────────────────┤
│                 READ SIDE (Cheap)                 │
│                                                  │
│  REST API (FastAPI) ─→ filter, search, detail    │
│  MCP Server ─→ find_packages, get_package        │
│  Website ─→ browse, search, package pages        │
│                                                  │
│  All read from DB. No LLM calls at query time.   │
└─────────────────────────────────────────────────┘
```

## Tech Stack

- **Language**: Python 3.12+
- **API**: FastAPI
- **Database**: SQLite for local dev (migrate to Postgres for production)
- **MCP Server**: Python, built on FastAPI layer
- **Frontend**: Simple Jinja2 templates or static HTML (no JS framework needed for MVP)
- **Evaluation agents**: Python + Anthropic API (Haiku for cost efficiency)
- **Package management**: uv
- **Local run**: `docker compose up` or `uv run` directly

## Non-Goals for MVP

- No user accounts / authentication
- No vendor self-service portal
- No payment processing
- No FQ Score (functional quality) — AF Score only for v1
- No real-time monitoring / uptime tracking
- No CI/CD pipeline
