# Assay — Claude Code Project Instructions

## Multi-Session Coordination

**Multiple Claude sessions may be working on this repo simultaneously.**

Before starting any work:
1. `git pull` to get latest state
2. Read `.claude/WORKBOARD.md` for available tasks and what's in progress
3. Check `.claude/active/` for files describing active work by other sessions
4. Claim your work item before starting (see protocol in WORKBOARD.md)
5. Use `git worktree` for any non-trivial changes to avoid conflicts on main

## Project Overview

Assay is an agentic software quality platform that rates MCP servers, APIs, and SDKs across three dimensions: Agent Friendliness (AF), Security, and Reliability.

- **Stack**: Python 3.12+, FastAPI, SQLAlchemy, Jinja2 templates, SQLite (local) / Postgres (Cloud SQL production)
- **Production**: Deployed on GCP Cloud Run (us-central1), domain: assay.tools
- **DB**: Cloud SQL Postgres instance `assay-db` (business-34-incubator:us-central1:assay-db), connected via Cloud SQL Auth Proxy
- **Container**: `us-central1-docker.pkg.dev/business-34-incubator/assay/assay:latest`
- **Backups**: Cloud SQL automated daily backups at 06:00 UTC, 7-day retention, point-in-time recovery

## Key Architecture

**Read `ARCHITECTURE.md` for full infrastructure reference** — secrets, services, DNS, Stripe, email architecture, source code layout, and how to access everything.

Key source paths:
- `src/assay/api/routes.py` — REST API (`/v1/...`)
- `src/assay/api/web_routes.py` — Server-rendered HTML pages
- `src/assay/api/payments.py` — Stripe checkout, webhooks, report delivery
- `src/assay/models/package.py` — All SQLAlchemy models
- `src/assay/evaluation/discovery.py` — Discovery agent + canonical CATEGORIES dict (16 categories)
- `src/assay/evaluation/scheduler.py` — 3-tier priority scheduler (flagged → unevaluated → stale)
- `src/assay/evaluation/loader.py` — Loads evaluation JSON into DB (normalizes categories to canonical list)
- `src/assay/notifications/email.py` — Resend SDK: transactional email (confirmations, report delivery)
- `src/assay/reports/` — Report generation (narratives via Claude Opus, PDF via WeasyPrint)
- `src/assay/mcp_server/` — Assay's own MCP server
- `src/assay/templates/` — Jinja2 templates
- `reports/` — Report templates and generation scripts (quarterly, package eval)

## Important Conventions

- Categories are canonical: 15 + "other", defined in `discovery.py:CATEGORIES`. The loader normalizes unknown slugs to "other". Never create ad-hoc categories.
- `Category.package_count` returns **evaluated** packages only (af_score IS NOT NULL), not total cataloged.
- Stats distinguish "evaluated" (has AF score) from "cataloged" (all packages in DB).
- Deploys require building and pushing a container, then updating Cloud Run. See Dockerfile for build config.
