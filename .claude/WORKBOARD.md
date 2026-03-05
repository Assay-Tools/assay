# Assay Workboard

Coordination file for multiple Claude sessions working on this repo.

## Protocol

### Before Starting Work
1. `git pull` to get latest workboard and active claims
2. Read this file and check `.claude/active/` for in-progress work
3. Pick an unclaimed item (or propose new work)
4. Create a claim file: `.claude/active/<topic>.md` with your focus, files you'll touch, and timestamp
5. `git add .claude/active/<topic>.md && git commit -m "claim: <topic>" && git push`
6. **Use a worktree** (`git worktree add`) if touching files that other sessions might also edit

### While Working
- Commit and push regularly to your branch (if using worktree) or to main (if safe)
- If you discover work that overlaps with another claim, stop and note it in your claim file

### When Done
1. Merge your worktree branch (if applicable)
2. Move your item to "Completed" below
3. Delete your claim file from `.claude/active/`
4. Commit and push

### Conflict Avoidance
- **Claim files are per-session** — never edit another session's claim file
- **Workboard edits** — only add items or move your own items between sections
- **When in doubt, use a worktree** — especially for multi-file changes
- **File-level ownership** — if two claims touch the same file, coordinate via the workboard or ask AJ

---

## Available Work

Items ready to be claimed. Roughly priority-ordered within each phase.

---

### Phase 1: Revenue Infrastructure (BLOCKING — must complete before any paid transactions)

- [ ] **Stripe integration** — Stripe Checkout for one-time report purchases ($99) and subscription billing ($3/mo monitoring). Create Stripe account, add `stripe` dependency, implement checkout session creation + webhook handler for `checkout.session.completed` and `customer.subscription.*` events. Store payment status on orders. Environment: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_REPORT` (one-time), `STRIPE_PRICE_MONITORING` (recurring). **Files**: new `src/assay/api/payments.py`, update `pyproject.toml`
- [ ] **Report delivery pipeline** — After Stripe payment confirmed, generate PDF report (use `weasyprint` or `reportlab`), store in S3/R2 or local filesystem, email download link to buyer. Connect to the existing `reports/generate_package_eval.py` script. **Files**: new `src/assay/reports/delivery.py`, new `src/assay/api/report_routes.py`
- [ ] **Email sending infrastructure** — Transactional email for report delivery, payment confirmations, and future score-change notifications. Use Resend or Postmark (not raw SMTP). **Files**: new `src/assay/notifications/email.py`. **Note**: AJ must approve the sending service choice and create the account
- [ ] **Buy report flow (web)** — "Buy Full Report — $99" button on package detail pages → Stripe Checkout → delivery. Only show for packages with enough data for a meaningful report. **Files**: update `templates/package_detail.html`, new `templates/report_purchase.html`, `templates/report_confirmation.html`
- [ ] **Basic bookkeeping** — Simple revenue/expense tracking. Could be as minimal as a CSV/JSON log of transactions pulled from Stripe webhook events, or a lightweight admin page. Enough for tax reporting. **Files**: new `src/assay/admin/accounting.py` or `scripts/export_transactions.py`

### Phase 2: Monitoring Product (enables $3/mo recurring revenue)

- [ ] **User accounts** — Registration + login for package monitoring subscribers. Email/password or magic link auth. Store in DB. JWT or session-based. **Files**: new `src/assay/models/user.py`, new `src/assay/api/auth_routes.py`, new templates for login/register
- [ ] **Package monitoring subscriptions** — Authenticated users can subscribe to packages ($3/mo each via Stripe). Dashboard showing subscribed packages, current scores, trends. **Files**: new `src/assay/models/subscription.py`, new `src/assay/api/subscription_routes.py`, new `templates/dashboard.html`
- [ ] **Score history tracking** — Record score snapshots over time (monthly or on each re-evaluation). Enables trend charts and change detection. Currently scores are single current values with no history. **Files**: new `src/assay/models/score_history.py`, migration script
- [ ] **Score change notifications** — When a monitored package's score changes, email the subscriber with old→new scores and explanation. Depends on: email infrastructure, score history, user accounts. **Files**: update `src/assay/notifications/email.py`

### Phase 3: Data Quality & Automation

- [ ] **Score backfill** — 500+ existing evaluations use old schema with only top-level security_score and no sub-component breakdown or reliability_score. Re-evaluate to populate all 14 sub-components. Can be batched via the evaluation skill
- [ ] **Automated re-evaluation pipeline** — Scheduled re-evaluation of stale packages (>90 days). Could be a cron job, Railway scheduled task, or GitHub Action that triggers the evaluation skill. Prioritize by: staleness, popularity, monitoring subscribers
- [x] **Data freshness dashboard** — Admin view showing evaluation coverage, staleness distribution, queue depth, and re-evaluation velocity

### Phase 4: Soft Launch — Trusted Feedback (do BEFORE public launch)

- [ ] **Daniel Miessler outreach** — Personal message to Daniel with link to assay.tools. He's in the AI/security space, runs Fabric (an MCP-adjacent tool), and AJ has an existing relationship. Ask for honest feedback on scoring methodology, UX, and whether the $99 report is compelling. Share via DM (not public). **Goal**: Get a credible practitioner's gut check before going wide
- [ ] **Trusted beta testers (5-10)** — Identify 5-10 people from AJ's network (security, AI, DevOps communities) who would give honest feedback. Send personal invites with specific questions: Is the scoring credible? Would you pay $99 for a report? What's missing? Collect feedback in a structured doc
- [ ] **Feedback collection mechanism** — Simple way for beta testers to submit feedback. Could be a Google Form, GitHub Discussions, or a `/feedback` page on the site. Low effort, high signal
- [ ] **Beta fixes sprint** — Reserve capacity to act on feedback from Daniel and beta testers before going public. Fix credibility issues, UX problems, or scoring methodology concerns

### Phase 5: Public Launch — Maximum Visibility

- [ ] **Hacker News submission** — "Show HN: Assay — Agent-readiness ratings for APIs and MCP servers". Timing matters: submit Tuesday-Thursday ~11am ET. Have answers ready for: How are scores calculated? Why should I trust this? What's the business model? AJ should be the one to post and respond to comments
- [ ] **Reddit launch posts** — Submit to relevant subreddits with tailored messaging:
  - `r/programming` — technical angle, scoring methodology
  - `r/machinelearning` / `r/artificial` — AI agent tooling angle
  - `r/selfhosted` — MCP server ratings angle
  - `r/SideProject` — indie builder story
  - Space posts 1-2 days apart, don't carpet-bomb same day
- [ ] **Daniel Miessler's Discord (Fabric community)** — Share in the Fabric Discord where MCP/AI tool builders hang out. Daniel's blessing from Phase 4 helps here. Focus on how Assay rates MCP servers specifically
- [ ] **Product Hunt launch** — Consider a Product Hunt submission. Good for visibility with indie dev / startup audience. Prep: good screenshots, one-liner, maker comment, hunter if possible
- [ ] **Dev.to / Hashnode blog post** — "How We Rate 7,000 APIs for Agent-Readiness" — technical deep-dive on scoring methodology. Establishes credibility, drives organic traffic, good backlink for SEO

### Phase 6: Customer Generation & Growth

- [ ] **Prospecting outreach to package maintainers** — The warm outreach play: for top-scored packages (AF 80+), reach out to maintainers with their score as a conversation opener. "Your package scored 87/100 on agent-friendliness — here's why." Links to full evaluation report purchase. Prioritize: packages with 55-75 scores (room to improve = report value), high GitHub stars, active development
- [ ] **Outreach templates** — Draft 3-4 email/DM templates for different scenarios: (1) high scorer congratulations, (2) mid-scorer improvement opportunity, (3) new package discovered, (4) re-evaluation score change. AJ reviews before any outbound
- [ ] **LinkedIn presence** — Post about Assay on AJ's LinkedIn. Share Q1 ecosystem report findings as thought leadership. Tag relevant package maintainers when discussing their scores (with permission)
- [x] **SEO basics** — Meta descriptions, OG tags, structured data (JSON-LD for SoftwareApplication ratings), sitemap.xml, robots.txt review. The directory should rank for "[package name] agent readiness" queries
- [ ] **Content calendar** — Recurring content plan: monthly "Top Movers" post (packages whose scores changed most), quarterly ecosystem report (already templated), category spotlights. Builds organic traffic and newsletter subscribers
- [ ] **Email list / newsletter** — Capture emails via Q1 report download (gated PDF) and optional site signup. Monthly digest of score changes, new evaluations, ecosystem trends. Nurtures leads toward $99 reports and $3/mo monitoring

### Phase 7: Product Expansion (Q3+ 2026)

- [ ] **Certified Agent-Ready program ($299/mo)** — Embeddable verified badge, priority re-evaluations, competitive reports, improvement consulting. Requires brand recognition first — don't launch until the directory has credibility
- [ ] **Community evaluation network** — Allow external contributors to submit evaluations (beyond API key holders). Reputation system, review queue, contributor leaderboard. Scales evaluation capacity beyond what agentic automation can handle alone
- [ ] **Comparison widgets** — Embeddable "Assay Score" badges for READMEs and docs sites (like shields.io). Free marketing — every badge is a backlink. `![Assay AF Score](https://assay.tools/badge/{package_id}.svg)`

---

## In Progress

*Check `.claude/active/` for details on each.*

(none currently)

---

## Completed

- [x] **Category consolidation** — 147→16 categories, stats consistency fix (2026-03-04)
- [x] **Package evaluation report** — $99 report template + generation script (2026-03-04)
- [x] **Q1 ecosystem report** — Quarterly report template + generation + full Q1-2026 output (2026-03-04)
- [x] **BUSINESS.md** — Business model, pricing, agentic operating philosophy (2026-03-04)
- [x] **SSL fix** — Railway cert provisioning via Cloudflare TXT record (2026-03-04)
- [x] **llms.txt + rate limiting** — `/llms.txt`, `/llms-full.txt` routes + slowapi 100/day on all `/v1/*` endpoints (2026-03-04)
- [x] **Test suite** — 49 pytest tests covering models, API routes (packages, categories, compare, stats, queue) (2026-03-04)
- [x] **CI/CD pipeline** — GitHub Actions lint (ruff) + test (pytest) on push/PR, CI badge in README (2026-03-04)
- [x] **Linting pass** — 64 violations fixed (25 auto-fix + 39 E501 line-length) (2026-03-04)
- [x] **OpenAPI spec polish** — tag descriptions, endpoint docstrings, schema field descriptions, API metadata (2026-03-04)
- [x] **API completeness** — score dimension filters, change feed endpoint, category leaderboards + 16 new tests (2026-03-04)
- [x] **Website polish** — staleness badge, radar chart, prominent evaluation date (2026-03-04)
- [x] **Disclaimer on about page** — as-is disclaimer, no warranty/guarantee/certification language (2026-03-04)
- [x] **Correction/dispute process** — score disputes section on about page with GitHub issues + email contact (2026-03-04)
- [x] **Submission API** — `POST /v1/evaluations` with Pydantic validation, pending queue, 11 tests (2026-03-04)
- [x] **Auth for submissions** — X-Api-Key header auth, comma-separated keys in config (2026-03-04)
- [x] **Evaluation review queue** — pending/approve/reject endpoints, PendingEvaluation model (2026-03-04)
- [x] **Evaluation skill** — Claude Code `/evaluate` slash command for package evaluation (2026-03-04)
- [x] **CLI tool** — `assay check/compare/stale` with ASCII output + --json, 5 tests (2026-03-04)
- [x] **SEO basics** — meta descriptions, OG tags, JSON-LD, sitemap.xml, robots.txt, 11 tests (2026-03-04)
- [x] **Data freshness dashboard** — /admin/freshness with coverage, staleness, category breakdown, 4 tests (2026-03-04)
