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

### Phase 0: Critical Fixes (BLOCKING — do before ANY public launch or payments)

**Legal (AJ must handle personally)**:
- [ ] **Form LLC + EIN** — File LLC in home state ($50-200), get EIN from IRS (free, online, immediate), open business bank account. Without this, every legal claim reaches personal assets. **Must complete before Stripe setup or any outbound prospecting**
- [ ] **Terms of Service** — Binding legal doc linked from every page footer. Must include: scores are opinions not warranties, no-reliance clause, limitation of liability (capped at fees paid in last 12 months), API usage restrictions, mandatory arbitration, class action waiver, IP ownership. Use Termly/similar as starting point. **Files**: new `templates/pages/terms.html`, update `templates/base.html` footer
- [ ] **Privacy Policy** — Stripe requires this before account creation. Cover: data collected (IPs, API keys, emails, payment info via Stripe), purpose, storage, sharing, deletion requests. GDPR + CCPA basics. **Files**: new `templates/pages/privacy.html`, update footer
- [ ] **Refund policy** — Define before accepting money. Recommend: full refund within 14 days for reports, subscriptions cancel at end of billing period

**Security (sessions can claim)**:
- [ ] **Rotate production credentials** — `.secrets` file on disk contains live DB password on publicly-accessible Postgres proxy. Rotate DB password in Railway, delete `.secrets`, use env vars exclusively. Also rotate Railway deploy token and Gmail app password. **CRITICAL**
- [x] **Fix CORS configuration** — `allow_origins=["*"]` + `allow_credentials=True` is dangerous. Drop `allow_credentials` or set explicit origin. **File**: `src/assay/api/app.py` lines 48-55
- [x] **Separate admin vs submitter API keys** — All keys have identical permissions — submitters can approve own evaluations. Split into `SUBMISSION_API_KEYS` / `ADMIN_API_KEYS`. **File**: `src/assay/api/submission_routes.py`
- [x] **Sort field whitelist** — `getattr(Package, sort_field)` allows probing any model attribute. Add allowlist like leaderboard endpoint does. **File**: `src/assay/api/routes.py` line 124
- [x] **Sanitize LIKE wildcards** — Escape `%` and `_` in search input before ILIKE. **File**: `src/assay/api/web_routes.py` lines 153-160
- [x] **Add security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`

**Code Quality (sessions can claim)**:
- [ ] **Fix AF weight mismatch** — `evaluator.py` uses different weights than `llms-full.txt` documents. Trust-destroying if a maintainer can't reproduce their score. Verify correct values, fix the other
- [ ] **Fix Category.package_count N+1** — Iterates all packages in Python. Use SQL COUNT. **File**: `src/assay/models/package.py` lines 420-423
- [x] **Fix infinite recursion on GitHub 403** — `fetch_github_metadata` recurses with no max retry. Add counter (max 3). **File**: `src/assay/evaluation/evaluator.py` lines 256-259
- [x] **Stop leaking exception details** — Submission route returns raw exception messages. Log internally, return generic error. **File**: `src/assay/api/submission_routes.py` lines 164-168
- [ ] **Strengthen disclaimer language** — Add "scores are editorial opinions, not statements of fact" framing. Add "as of [date]" to every score display. **File**: `templates/pages/about.html`

### Website & UX (high impact for launch readiness — sessions can claim)

- [ ] **"Report inaccuracy" link on package pages** — Link on every package detail page → pre-filled GitHub issue. Dispute path currently buried on `/about`. 30 min effort, huge trust signal. **File**: `templates/pages/package_detail.html`
- [ ] **Developer docs page** — Proper `/developers` page: API getting-started, curl examples, rate limit docs, MCP config JSON, OpenAPI link. Currently API consumers hit raw Swagger. **Files**: new `templates/pages/developers.html`, update `web_routes.py`
- [ ] **Embeddable score badges** — `/badge/{package_id}.svg` shields.io-style SVG. Every README embed = permanent backlink. Highest-leverage organic growth. Moved up from Phase 7. **File**: new route in `web_routes.py`
- [ ] **Add text search to API** — Web supports `q` search but API `/v1/packages` does not. Agents can't search by name. **File**: `src/assay/api/routes.py`
- [ ] **RSS feed** — `/feed.xml` for recently evaluated packages. **File**: new route in `web_routes.py`
- [ ] **Email capture** — "Subscribe for weekly evaluations" on homepage. Primary re-engagement channel — currently every visitor is one-and-done. **File**: `templates/pages/index.html`
- [ ] **Team/about enhancement** — Who runs this? Add brief human attribution. **File**: `templates/pages/about.html`
- [ ] **Methodology page** — Dedicated deep-dive: data sources, LLM evaluation, weighting, limitations, re-eval frequency. Dual purpose: trust + legal protection. **Files**: new `templates/pages/methodology.html`
- [ ] **Fix /docs footer link** — Points to raw Swagger. Relabel or redirect to `/developers`. **File**: `templates/base.html`

### Strategic Additions (from business/GTM review)

- [ ] **GitHub Action for CI** — Free `assay-score` Action that checks AF Score in CI. Every repo that adds it = marketing surface + backlink. Higher-leverage growth than cold email
- [ ] **Publish scoring methodology openly** — Like OpenSSF Scorecard. Transparency builds trust. Blog post + methodology page
- [ ] **Target companies, not just individuals** — Reframe $99 report as "competitive analysis" for DevRel teams. Consider $499-999 tier with report + 30-min call. Update BUSINESS.md
- [ ] **Partnership: Smithery.ai** — They're the MCP directory, Assay is the quality layer. Reach out after public launch with data, not a pitch deck
- [ ] **Partnership: Agent frameworks** — LangChain, CrewAI, AutoGen, Semantic Kernel. If their tool selection references Assay scores = instant demand
- [ ] **Methodology Advisory Board** — 2-3 named credible people (Daniel Miessler first). Credibility signal + legal armor. Costs nothing
- [ ] **Seed modelcontextprotocol/servers GitHub discussions** — People literally asking "which MCP servers are good?" in those threads. Be genuinely helpful with links to relevant Assay data

### Phase 1: Revenue Infrastructure (BLOCKING — must complete before any paid transactions)

- [x] ~~**Stripe integration** — done, moved to Completed~~
- [x] ~~**Report delivery pipeline** — done, moved to Completed~~
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
- [x] **Outreach templates** — Draft 3-4 email/DM templates for different scenarios: (1) high scorer congratulations, (2) mid-scorer improvement opportunity, (3) new package discovered, (4) re-evaluation score change. AJ reviews before any outbound
- [ ] **LinkedIn presence** — Post about Assay on AJ's LinkedIn. Share Q1 ecosystem report findings as thought leadership. Tag relevant package maintainers when discussing their scores (with permission)
- [x] ~~**SEO basics** — moved to Completed~~
- [ ] **Content calendar** — Recurring content plan: monthly "Top Movers" post (packages whose scores changed most), quarterly ecosystem report (already templated), category spotlights. Builds organic traffic and newsletter subscribers
- [ ] **Email list / newsletter** — Capture emails via Q1 report download (gated PDF) and optional site signup. Monthly digest of score changes, new evaluations, ecosystem trends. Nurtures leads toward $99 reports and $3/mo monitoring

### Phase 7: Product Expansion (Q3+ 2026)

- [ ] **Certified Agent-Ready program ($299/mo)** — Embeddable verified badge, priority re-evaluations, competitive reports, improvement consulting. Requires brand recognition first — don't launch until the directory has credibility
- [ ] **Community evaluation network** — Allow external contributors to submit evaluations (beyond API key holders). Reputation system, review queue, contributor leaderboard. Scales evaluation capacity beyond what agentic automation can handle alone
- [ ] **Comparison widgets** — Embeddable side-by-side comparison iframes for docs sites and blog posts. `<iframe src="https://assay.tools/embed/compare?ids=a,b">`

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
- [x] **Stripe integration** — checkout sessions, webhook handler, Order model, order status endpoint, 9 tests (2026-03-04)
- [x] **Report delivery pipeline** — post-payment report generation, download endpoint, success page, 16 total payment tests (2026-03-04)
