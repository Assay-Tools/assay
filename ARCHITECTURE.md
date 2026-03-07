# Assay — Architecture & Infrastructure Reference

**Last Updated**: 2026-03-07

Quick reference for where everything lives, how services connect, and how to access them. Read this at the start of any session touching Assay infrastructure.

---

## Service Map

```
                        ┌─────────────────────┐
                        │   assay.tools        │
                        │   (Cloudflare DNS)   │
                        └──────────┬──────────┘
                                   │ CNAME
                        ┌──────────▼──────────┐
                        │   Railway            │
                        │   FastAPI app        │
                        │   (auto-deploy main) │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
             ┌──────▼─────┐ ┌─────▼─────┐ ┌─────▼──────┐
             │  Postgres   │ │  Stripe   │ │  Resend    │
             │  (Railway)  │ │  (payments)│ │  (email)   │
             └────────────┘ └───────────┘ └────────────┘
```

---

## Hosting & Deployment

| Component | Service | Details |
|-----------|---------|---------|
| **App** | Railway | Auto-deploys from `main` branch. Python 3.12, FastAPI, Uvicorn. |
| **Database** | Railway Postgres | Public proxy: `interchange.proxy.rlwy.net:42133` |
| **Domain** | Porkbun (registrar) → Cloudflare (DNS) | Zone: `08a7c326ad4b9fd8cffeb1acb7d89f48` |
| **Repo** | GitHub (`Assay-Tools/assay`) | CI: GitHub Actions (lint + test) |

**Railway CLI**: `railway` (v4.31+). Run `cd ~/git/assay && railway <command>`.
- `railway variables list` — show all env vars
- `railway variables set KEY=VALUE` — set a production env var
- `railway logs` — tail production logs

---

## Secrets Management

**Source of truth**: GCP Secret Manager, project `business-34-incubator`.

```bash
# List all secrets
gcloud secrets list --project=business-34-incubator

# Read a secret
gcloud secrets versions access latest --secret=ASSAY_RESEND_API_KEY --project=business-34-incubator

# Create a new secret
echo -n "value" | gcloud secrets create SECRET_NAME --project=business-34-incubator --data-file=-
```

### Secret Inventory

| GCP Secret | Railway Env Var | Purpose |
|-----------|----------------|---------|
| `ASSAY_ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` | Claude API for report narrative generation |
| `ASSAY_STRIPE_SECRET_KEY` | `STRIPE_SECRET_KEY` | Stripe API (live) |
| `ASSAY_STRIPE_WEBHOOK_SECRET` | `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature verification |
| `ASSAY_RESEND_API_KEY` | `RESEND_API_KEY` | Resend transactional email API |
| `ASSAY_ADMIN_API_KEY` | `ADMIN_API_KEYS` | Admin endpoint authentication |
| `ASSAY_DATABASE_URL` | `DATABASE_URL` | Postgres connection string |
| `ASSAY_SMTP_PASS` | `SMTP_PASS` | Migadu mailbox password (legacy, inbound email) |
| `ASSAY_GCS_SA_KEY` | `GCS_SA_KEY` | GCS service account key JSON (report storage) |

### Other Railway Env Vars (not secret-managed)

| Var | Value | Purpose |
|-----|-------|---------|
| `SMTP_USER` | `hello@assay.tools` | Migadu sender identity |
| `SMTP_HOST` | `smtp.migadu.com` | Migadu SMTP server |
| `SMTP_PORT` | `465` | Migadu SMTP port (SSL) |
| `STRIPE_PRICE_REPORT` | `price_1T8Q3D...wiTP` | Stripe Price ID: $99 report (live) |
| `STRIPE_PRICE_BRIEF` | `price_1T8Q3A...H2v8T` | Stripe Price ID: $3 brief (live) |
| `STRIPE_PRICE_MONITORING` | `price_1T8Q3D...OKmF` | Stripe Price ID: $3/mo monitoring (live) |
| `STRIPE_PRICE_SUPPORT` | `price_1T8Q3B...Xw9K` | Stripe Price ID: custom support (live) |
| `GCS_BUCKET` | `assay-reports` | GCS bucket for durable report storage |

### Local Development

- `.secrets` file in repo root (gitignored) — loaded by pydantic-settings alongside `.env`
- `.env.example` documents all available settings

---

## Email Architecture

Two separate services for two separate concerns:

| | Resend | Migadu |
|---|--------|--------|
| **Role** | Transactional outbound | Mailbox (inbound + conversational) |
| **Use cases** | Order confirmations, report delivery (with PDF/md attachments), score-change alerts | Receiving customer replies, support queries, 1:1 correspondence |
| **Access from app** | Resend SDK (`src/assay/notifications/email.py`) | Legacy SMTP config (kept for backward compat) |
| **Access for reading** | N/A | MCP server `gmail-assay` (Migadu IMAP) |
| **From address** | `Assay Tools <hello@assay.tools>` | `hello@assay.tools` |
| **Reply-to** | `hello@assay.tools` (routes replies to Migadu inbox) | N/A |

### DNS Records (Cloudflare)

**Migadu (root domain)**:
- MX: `aspmx1.migadu.com` (10), `aspmx2.migadu.com` (20)
- TXT SPF: `v=spf1 include:spf.migadu.com -all`
- CNAME DKIM: `key1._domainkey`, `key2._domainkey`, `key3._domainkey` → migadu.com
- TXT DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@assay.tools`
- TXT verify: `hosted-email-verify=xnzwed2v`

**Resend (`send` subdomain — no conflict with Migadu)**:
- TXT DKIM: `resend._domainkey` → RSA public key
- MX: `send.assay.tools` → `feedback-smtp.us-east-1.amazonses.com` (10)
- TXT SPF: `send.assay.tools` → `v=spf1 include:amazonses.com ~all`

### Migadu Mailboxes & Aliases

- **Mailboxes**: `hello@assay.tools`, `admin@assay.tools`
- **Aliases**: `support@` → hello@, `billing@` → hello@

---

## Cloudflare

**Zone ID**: `08a7c326ad4b9fd8cffeb1acb7d89f48`
**API Token**: GCP Secret Manager → `CLOUDFLARE_API_TOKEN`
**Account ID**: GCP Secret Manager → `CLOUDFLARE_ACCOUNT_ID`

```bash
# List DNS records
CF_TOKEN=$(gcloud secrets versions access latest --secret=CLOUDFLARE_API_TOKEN --project=business-34-incubator)
curl -s "https://api.cloudflare.com/client/v4/zones/08a7c326ad4b9fd8cffeb1acb7d89f48/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" | python3 -m json.tool
```

---

## GCS Report Storage

**Bucket**: `gs://assay-reports` (us-central1)
**Service account**: `assay-reports-rw@business-34-incubator.iam.gserviceaccount.com`
**Key structure**: `reports/{package_id}/{report_type}.{md,pdf}`

Reports are uploaded to GCS after generation and served from GCS when local files are missing (e.g., after container redeploy). Both brief and full report types are stored for cache reuse.

| Railway Env Var | Purpose |
|----------------|---------|
| `GCS_BUCKET` | Bucket name (`assay-reports`) |
| `GCS_SA_KEY` | Service account key JSON |

---

## Stripe

**Dashboard**: https://dashboard.stripe.com
**Account email**: ajvanbeest@gmail.com
**Mode**: Live
**Webhook endpoint**: `https://assay.tools/v1/webhooks/stripe`
**Events subscribed**: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`

### Products

| Product | Price ID | Amount | Type |
|---------|----------|--------|------|
| Full Evaluation Report | `price_1T83U1QMZHAaY3TRikxhlU8q` | $99.00 | One-time |
| Package Brief | `price_1T86jqQMZHAaY3TRFdBDFGqK` | $3.00 | One-time |
| Package Monitoring | `price_1T83U3QMZHAaY3TRtiMDdDQj` | $3.00/mo | Recurring |
| Support the Mission | `price_1T86k1QMZHAaY3TRUrinXoW5` | Custom (min $1) | One-time |

---

## Source Code Layout

```
src/assay/
├── api/                    # FastAPI routes
│   ├── app.py              # App factory, middleware, CORS, security headers
│   ├── routes.py           # REST API (/v1/packages, /v1/categories, /v1/stats, etc.)
│   ├── web_routes.py       # Server-rendered HTML pages
│   ├── admin_routes.py     # Admin endpoints (freshness, reevaluate, dashboard)
│   ├── auth_routes.py      # GitHub OAuth for contributor auth
│   ├── payments.py         # Stripe checkout, webhooks, report delivery, order status
│   ├── submission_routes.py # Community evaluation submission API
│   └── rate_limit.py       # slowapi rate limiting
├── auth/
│   ├── contributor.py      # Contributor model, trust tiers
│   └── github.py           # GitHub OAuth flow
├── evaluation/
│   ├── discovery.py        # 7-source package discovery + canonical CATEGORIES dict
│   ├── evaluator.py        # Batch evaluation runner
│   ├── scheduler.py        # 3-tier priority scheduler (flagged → unevaluated → stale)
│   ├── loader.py           # Load evaluation JSON into DB (normalizes categories)
│   ├── rubric.py           # Evidence-banded rubric v2 (14 sub-components)
│   └── sources/            # Discovery sources (github, smithery, npm, pypi, etc.)
├── heartbeat/              # Business health checks (site, data, feedback)
├── mcp_server/             # Assay's own MCP server (4 tools)
├── models/
│   ├── package.py          # Package, Category, Order, ScoreSnapshot, ReportCache, etc.
│   └── __init__.py         # Model exports
├── notifications/
│   └── email.py            # Resend SDK: order confirmations, report delivery
├── reports/
│   ├── delivery.py         # Report generation orchestration + caching
│   ├── narratives.py       # Claude Opus narrative generation (two-pass)
│   └── pdf.py              # Branded PDF generation (WeasyPrint)
├── templates/              # Jinja2 templates (pages/, embeds/)
├── static/                 # CSS, JS, evaluation guides
├── config.py               # pydantic-settings (loads .env + .secrets)
├── database.py             # SQLAlchemy engine + session
└── cli.py                  # CLI: assay check/compare/stale
```

---

## GitHub Actions

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `ci.yml` | On push/PR | Ruff lint + pytest (168 tests) |
| `discovery.yml` | 06:00 + 18:00 UTC daily | Run package discovery across 7 sources |
| `stale-check.yml` | 09:00 UTC Mondays | Create/update GitHub issue listing stale packages |

---

## Overnight Evaluation Sessions (PAUSED)

Two launchd jobs that ran Claude Code sessions for batch evaluation. **Currently unloaded** due to broad `git add .` sweeping unrelated work into commits.

| Job | Schedule | Prompt |
|-----|----------|--------|
| `com.assay.session1` | 22:31 daily | `scripts/session-1-business.md` (Sonnet) |
| `com.assay.session2` | 03:32 daily | `scripts/session-2-polish.md` (Sonnet) |

**Before re-enabling**: Fix `scripts/run-session.sh` to only `git add evaluations/ logs/`, not `git add .`. Consider running in a git worktree. See WORKBOARD.md for full details.

---

## Business Entity

- **Parent LLC**: Business 34 LLC (Illinois, filed 2026-03-05, awaiting approval)
- **DBA**: "Assay Tools" (file after LLC approved)
- **GCP Project**: `business-34-incubator` (billing: `016879-B9FEB8-5BD8AF`)
- **Incubator framework**: `~/git/agentic-incubator/`
- **Business state**: `~/ai-data/projects/business-incubator/active/assay/`

---

## Key Conventions

- **Categories are canonical**: 15 + "other", defined in `discovery.py:CATEGORIES`. The loader normalizes unknown slugs to "other". Never create ad-hoc categories.
- **`Category.package_count`** returns evaluated packages only (af_score IS NOT NULL), not total cataloged.
- **Stats distinguish** "evaluated" (has AF score) from "cataloged" (all packages in DB).
- **Railway auto-deploys** on push to main. Be confident before pushing.
- **Tests**: `cd ~/git/assay && .venv/bin/pytest -x -q` (168 passing as of 2026-03-07)
- **Lint**: `cd ~/git/assay && .venv/bin/ruff check src/`
