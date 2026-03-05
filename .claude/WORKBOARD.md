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
- [x] **Terms of Service** — DRAFT at /terms with all required clauses, footer link, AJ must review with lawyer (2026-03-04)
- [x] **Privacy Policy** — DRAFT at /privacy with GDPR/CCPA, footer link, AJ must review with lawyer (2026-03-04)
- [x] **Refund policy** — Included in ToS: 14-day full refund for reports, cancel-anytime for subs (2026-03-04)

**Security (sessions can claim)**:
- [ ] **Rotate production credentials** — `.secrets` file on disk contains live DB password on publicly-accessible Postgres proxy. Rotate DB password in Railway, delete `.secrets`, use env vars exclusively. Also rotate Railway deploy token and Gmail app password. **CRITICAL**
- [x] **Fix CORS configuration** — `allow_origins=["*"]` + `allow_credentials=True` is dangerous. Drop `allow_credentials` or set explicit origin. **File**: `src/assay/api/app.py` lines 48-55
- [x] **Separate admin vs submitter API keys** — All keys have identical permissions — submitters can approve own evaluations. Split into `SUBMISSION_API_KEYS` / `ADMIN_API_KEYS`. **File**: `src/assay/api/submission_routes.py`
- [x] **Sort field whitelist** — `getattr(Package, sort_field)` allows probing any model attribute. Add allowlist like leaderboard endpoint does. **File**: `src/assay/api/routes.py` line 124
- [x] **Sanitize LIKE wildcards** — Escape `%` and `_` in search input before ILIKE. **File**: `src/assay/api/web_routes.py` lines 153-160
- [x] **Add security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`

**Code Quality (sessions can claim)**:
- [x] **Fix AF weight mismatch** — Fixed llms-full.txt docs to match code weights (2026-03-04)
- [x] **Fix Category.package_count N+1** — hybrid_property with SQL COUNT subquery (2026-03-04)
- [x] **Fix infinite recursion on GitHub 403** — `fetch_github_metadata` recurses with no max retry. Add counter (max 3). **File**: `src/assay/evaluation/evaluator.py` lines 256-259
- [x] **Stop leaking exception details** — Submission route returns raw exception messages. Log internally, return generic error. **File**: `src/assay/api/submission_routes.py` lines 164-168
- [x] **Strengthen disclaimer language** — Editorial opinions framing + as-of-date on package pages (2026-03-04)

### Website & UX (high impact for launch readiness — sessions can claim)

- [x] **"Report inaccuracy" link on package pages** — Pre-filled GitHub issue link on every package page (2026-03-04)
- [x] **Developer docs page** — `/developers` with API getting-started, endpoints, examples, rate limits, MCP config, badges (2026-03-04)
- [x] **Embeddable score badges** — `/badge/{package_id}.svg` shields.io-style SVG with color coding (2026-03-04)
- [x] **Add text search to API** — `q` param on `/v1/packages` with ILIKE search (2026-03-04)
- [x] **RSS feed** — `/feed.xml` with 50 most recently evaluated packages (2026-03-04)
- [x] **Email capture** — EmailSubscriber model + /subscribe endpoint + homepage form (2026-03-04)
- [x] **Team/about enhancement** — "Who We Are" section with AJ attribution + methodology link (2026-03-04)
- [x] **Methodology page** — Full scoring breakdown with weights, data sources, evaluation process, limitations (2026-03-04)
- [x] **Fix /docs footer link** — Relabeled to "API" (2026-03-04)

### Strategic Additions (from business/GTM review)

- [x] **GitHub Action for CI** — Composite action at action.yml with min-score threshold, dimension selection, step summary (2026-03-04)
- [x] **Publish scoring methodology openly** — /methodology page with full weights, process, and limitations (2026-03-04)
- [ ] **Target companies, not just individuals** — Reframe $99 report as "competitive analysis" for DevRel teams. Consider $499-999 tier with report + 30-min call. Update BUSINESS.md
- [ ] **Partnership: Smithery.ai** — They're the MCP directory, Assay is the quality layer. Reach out after public launch with data, not a pitch deck
- [ ] **Partnership: Agent frameworks** — LangChain, CrewAI, AutoGen, Semantic Kernel. If their tool selection references Assay scores = instant demand
- [ ] **Methodology Advisory Board** — 2-3 named credible people (Daniel Miessler first). Credibility signal + legal armor. Costs nothing
- [ ] **Seed modelcontextprotocol/servers GitHub discussions** — People literally asking "which MCP servers are good?" in those threads. Be genuinely helpful with links to relevant Assay data

### Site Quality (BLOCKING — must fix before public launch)

- [ ] **Full site audit — link and content tree** — End-to-end crawl of every page and link on assay.tools. Produce a site tree showing: (1) pages with broken links, (2) pages missing content or showing placeholder data, (3) pages that work correctly. Output as a structured doc that can be split into individual fix tasks. Include: all nav links, footer links, package detail page links (API endpoint, agent guide, badge, report inaccuracy), developer docs examples, about page references, category pages, compare flow, feedback form, email capture, RSS feed, sitemap.xml, badge SVG endpoints, embed widgets. Test both with and without data.
- [ ] **Fix "Assay API" naming** — The developer docs and some pages reference "Claude API" as an example package. Review all user-facing copy to ensure when we're talking about *Assay's own API*, we call it "Assay API" not "Claude API". The Claude API is a *rated package*, not our product.

### Phase 1: Revenue Infrastructure (BLOCKING — must complete before any paid transactions)

**Stripe account setup (AJ must do)**:
- [ ] **Create Stripe account** — Sign up at stripe.com. Requires: legal business name (needs LLC first), EIN, business bank account. Get the API keys from the Stripe dashboard.
- [ ] **Create Stripe Products + Prices** — In Stripe dashboard: (1) Product "Package Evaluation Report" with one-time Price of $99.00, (2) Product "Package Monitoring" with recurring Price of $3.00/month. Copy the Price IDs (e.g., `price_xxx`).
- [ ] **Set Railway environment variables** — In Railway dashboard, set: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_REPORT` (one-time price ID), `STRIPE_PRICE_MONITORING` (recurring price ID). All four are required.
- [ ] **Configure Stripe webhook** — In Stripe dashboard → Developers → Webhooks: add endpoint `https://assay.tools/v1/webhooks/stripe`, subscribe to events: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET` env var.

**Stripe code fixes (sessions can claim)**:
- [ ] **Fix webhook signature bypass** — When `STRIPE_WEBHOOK_SECRET` is not set, the webhook handler skips signature verification entirely. In production, anyone could POST fake events and trigger order fulfillment. Add hard requirement: return 503 if webhook secret is missing. **File**: `src/assay/api/payments.py`
- [ ] **Fix orphan order creation** — Orders are created and committed *before* calling `stripe.checkout.Session.create()`. If the Stripe call fails, orphan orders with `status="pending"` accumulate forever. Create order after Stripe session succeeds, or rollback on failure. **File**: `src/assay/api/payments.py`
- [ ] **Fix buyReport() JS event handling** — The `buyReport()` function uses implicit global `event` object instead of passing it as a parameter. Fragile in strict mode. **File**: `templates/pages/package_detail.html`
- [ ] **Add Stripe vars to .env.example** — `.env.example` is missing all four Stripe variables. Anyone setting up the project won't know they're needed
- [ ] **Email sending infrastructure** — Transactional email for report delivery, payment confirmations, and future score-change notifications. Use Resend or Postmark (not raw SMTP). **Files**: new `src/assay/notifications/email.py`. **Note**: AJ must approve the sending service choice and create the account

### Phase 2: Monitoring Product (enables $3/mo recurring revenue)

- [ ] **User accounts** — Registration + login for package monitoring subscribers. Email/password or magic link auth. Store in DB. JWT or session-based. **Files**: new `src/assay/models/user.py`, new `src/assay/api/auth_routes.py`, new templates for login/register
- [ ] **Package monitoring subscriptions** — Authenticated users can subscribe to packages ($3/mo each via Stripe). Dashboard showing subscribed packages, current scores, trends. **Files**: new `src/assay/models/subscription.py`, new `src/assay/api/subscription_routes.py`, new `templates/dashboard.html`
- [x] **Score history tracking** — ScoreSnapshot model + /v1/packages/{id}/score-history API + auto-snapshot in loader, 5 tests (2026-03-04)
- [ ] **Score change notifications** — When a monitored package's score changes, email the subscriber with old→new scores and explanation. Depends on: email infrastructure, score history, user accounts. **Files**: update `src/assay/notifications/email.py`

### Phase 3: Data Quality & Automation

- [ ] **Score backfill** — 500+ existing evaluations use old schema with only top-level security_score and no sub-component breakdown or reliability_score. Re-evaluate to populate all 14 sub-components. Can be batched via the evaluation skill
- [x] **Automated re-evaluation pipeline** — Weekly GitHub Action + check_stale.py script, creates/updates issue with stale packages (2026-03-04)
- [x] **Data freshness dashboard** — Admin view showing evaluation coverage, staleness distribution, queue depth, and re-evaluation velocity

### Phase 4: Soft Launch — Trusted Feedback (do BEFORE public launch)

- [ ] **Daniel Miessler outreach** — Personal message to Daniel with link to assay.tools. He's in the AI/security space, runs Fabric (an MCP-adjacent tool), and AJ has an existing relationship. Ask for honest feedback on scoring methodology, UX, and whether the $99 report is compelling. Share via DM (not public). **Goal**: Get a credible practitioner's gut check before going wide
- [ ] **Trusted beta testers (5-10)** — Identify 5-10 people from AJ's network (security, AI, DevOps communities) who would give honest feedback. Send personal invites with specific questions: Is the scoring credible? Would you pay $99 for a report? What's missing? Collect feedback in a structured doc
- [x] **Feedback collection mechanism** — /feedback page with structured form, Feedback model, footer link, 6 tests (2026-03-04)
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
- [x] **Comparison widgets** — /embed/compare?ids=a,b self-contained iframe widget with inline styles, 3 tests (2026-03-04)

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
- [x] **Buy report flow (web)** — $99 button on package pages → Stripe Checkout → delivery (2026-03-04)
- [x] **Basic bookkeeping** — /admin/transactions (JSON/CSV) + /admin/revenue, admin key auth, 8 tests (2026-03-04)
