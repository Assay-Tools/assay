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
- [x] **Form "Business 34" LLC in Illinois** — FILED 2026-03-05. Business 34 LLC filed with Illinois Secretary of State ($150). Packet number: `1772707880498893`. Status check: https://apps.ilsos.gov/llcarticles/lLStatus.do — Up to 10 business days to process. **Next steps after approval**: Get EIN from IRS (free, online, immediate), open business bank account under Business 34 LLC, file "Assay Tools" DBA. When Assay graduates (consistent revenue), spin it out into its own LLC. **Must complete EIN + bank account before Stripe setup or any outbound prospecting**
- [x] **Terms of Service** — DRAFT at /terms with all required clauses, footer link, AJ must review with lawyer (2026-03-04)
- [x] **Privacy Policy** — DRAFT at /privacy with GDPR/CCPA, footer link, AJ must review with lawyer (2026-03-04)
- [x] **Refund policy** — Included in ToS: 14-day full refund for reports, cancel-anytime for subs (2026-03-04)

**Security (sessions can claim)**:
- [x] **Rotate production credentials** — DB password rotated via Railway CLI + ALTER USER (2026-03-06). `.secrets` file deleted. `migrate_scorecard.py` .secrets fallback removed. Railway token in old .secrets was already invalid (interactive login used). **Remaining**: Gmail app password rotation requires AJ to visit Google security settings manually.
- [x] **Fix CORS configuration** — `allow_origins=["*"]` + `allow_credentials=True` is dangerous. Drop `allow_credentials` or set explicit origin. **File**: `src/assay/api/app.py` lines 48-55
- [x] **Separate admin vs submitter API keys** — All keys have identical permissions — submitters can approve own evaluations. Split into `SUBMISSION_API_KEYS` / `ADMIN_API_KEYS`. **File**: `src/assay/api/submission_routes.py`
- [x] **Sort field whitelist** — `getattr(Package, sort_field)` allows probing any model attribute. Add allowlist like leaderboard endpoint does. **File**: `src/assay/api/routes.py` line 124
- [x] **Sanitize LIKE wildcards** — Escape `%` and `_` in search input before ILIKE. **File**: `src/assay/api/web_routes.py` lines 153-160
- [x] **Add security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`
- [x] **Fix IDOR on order endpoints** — Order success pages, status API, and report downloads used sequential integer IDs (`/orders/1/success`), trivially guessable. Added cryptographic `access_token` (secrets.token_urlsafe) to Order model. All public URLs now use unguessable token. Migration backfills existing orders. 5 new tests. (2026-03-07)
- [x] **Comprehensive security audit — 20 findings fixed** (2026-03-07):
  - **H1**: OAuth CSRF — state stored in signed HttpOnly cookie, validated on callback with `hmac.compare_digest`
  - **H2**: Timing-safe API key comparison — all auth functions use `hmac.compare_digest()` instead of `in`
  - **H3**: XML injection — `_xml_escape()` applied to package IDs in RSS feed and sitemap
  - **M1**: `/admin/freshness` now requires admin API key (header or `?key=` param)
  - **M3**: Path traversal protection on report download (`.resolve()` + `.is_relative_to()`)
  - **M4**: `/embed/` routes exempted from `X-Frame-Options: DENY`
  - **M5**: Admin key fallback to submission keys removed
  - **M6**: Webhook endpoint rate-limited (120/min)
  - **M7**: Race condition guard in background report generation
  - **M8**: LIKE wildcard escaping in MCP server search
  - **L1**: `report_path` removed from API response (replaced with `has_report` boolean)
  - **L2**: Operator email moved to config setting
  - **L3**: Content-Security-Policy header added
  - **L4**: Customer emails masked in all log messages
  - **L5**: API key page has `Cache-Control: no-store`
  - **L7**: Tailwind CDN pinned to v3.4.17
  - **L9**: `JSONDecodeError` handled in model properties
  - Tests updated (200 passing), test for freshness auth + admin fallback removal

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

- [x] **Full site audit — link and content tree** — All 16 main pages return 200, no broken links. Findings: (1) Categories page has 2 empty categories (Content Management, Agent Skills — 0 evaluated packages), (2) Compare page UX is weak (no visible Quick Add controls, massive unstructured package dump), (3) Methodology nav renders twice (cosmetic). (2026-03-05)
- [x] **Fix "Assay API" naming** — Developer docs examples changed from `claude-api` to `stripe-api` to avoid confusion between Assay's API and the Claude API rated package (2026-03-05)

### Website Analytics & Tracking (should be live before public launch)

**Philosophy**: Track enough to extract real business value (traffic sources, conversion, launch effectiveness) while respecting privacy and not adding to internet shitification. Cookie-free analytics for the baseline — no consent banner needed. Opt-in only for anything that requires cookies or PII.

**Analytics platform (AJ picks one)**:
- [ ] **Choose and deploy privacy-first analytics** — Evaluate and pick ONE:
  - **Plausible** (~$9/mo, hosted) — No cookies, no PII, GDPR/CCPA compliant by default, lightweight script (~1KB), open-source core. Dashboard shows: traffic, sources, top pages, conversions, countries. Good enough for 90% of business questions. No consent banner required.
  - **Umami** (free, self-hosted on Railway) — Same privacy model as Plausible but self-hosted. Zero additional cost if deployed alongside Assay on Railway. Slightly more setup work. Open source.
  - **Fathom** (~$14/mo) — Similar to Plausible, slightly more enterprise-focused.
  - **Recommendation**: Umami self-hosted (fits the $23/mo budget, privacy-first, full control) or Plausible hosted (least friction, $9/mo is worth avoiding self-hosting headaches).

**Core tracking (no cookies, no consent needed)**:
- [ ] **Add analytics script to base template** — Single `<script>` tag in `base.html`. Should track: page views, referral sources, UTM parameters, device/browser/country, session duration. No cookies = no consent banner for this. **File**: `src/assay/templates/base.html`
- [ ] **Define conversion goals** — Set up goal tracking for key business events: (1) report purchase click, (2) email signup, (3) API docs visit, (4) feedback submission, (5) badge embed code copy, (6) comparison started. These are just URL/event matches — still no cookies needed with Plausible/Umami.
- [x] **UTM parameter strategy for launch** — Full UTM scheme documented in `docs/utm-strategy.md` covering all launch channels (2026-03-05)

**Consent & enhanced tracking (opt-in only)**:
- [ ] **Privacy-respecting consent mechanism** — Simple, honest preference center (NOT a dark-pattern cookie wall). Two tiers: (1) **Essential only** (default, cookie-free analytics, no PII) — always on, no consent needed. (2) **Enhanced** (opt-in) — enables Stripe conversion tracking, optional session replay for UX debugging, and any future integrations that require cookies. A small, non-intrusive banner: "We use cookie-free analytics by default. [Learn more] [Enable enhanced tracking]". Store preference in localStorage (not a cookie, irony intended). **Files**: new partial template, update `base.html`, update Privacy Policy
- [ ] **Update Privacy Policy for analytics** — Add section describing: what we track (page views, referrals, country — no PII), what tool we use (open-source, privacy-first), what enhanced tracking adds if opted in, how to opt out. Must stay aligned with the existing DRAFT privacy policy. **File**: update `src/assay/templates/pages/privacy.html`

**Business intelligence (post-launch)**:
- [ ] **Launch effectiveness dashboard** — After public launch, build a simple internal view showing: traffic by source/day, conversion rates by channel, which Reddit/HN/Discord posts drove the most engaged traffic. Helps decide where to invest future marketing effort. Can be a simple admin page or just a saved analytics dashboard view.
- [x] **API usage analytics** — Middleware tracks /v1/ call counts + errors per endpoint, logs slow requests. GET /admin/api-usage endpoint for stats. (2026-03-05)

### Phase 1: Revenue Infrastructure (BLOCKING — must complete before any paid transactions)

**Stripe account setup (AJ must do)**:
- [ ] **Create Stripe account** — Sign up at stripe.com. Requires: legal business name (needs LLC first), EIN, business bank account. Get the API keys from the Stripe dashboard.
- [ ] **Create Stripe Products + Prices** — In Stripe dashboard: (1) Product "Package Evaluation Report" with one-time Price of $99.00, (2) Product "Package Monitoring" with recurring Price of $3.00/month. Copy the Price IDs (e.g., `price_xxx`).
- [ ] **Set Railway environment variables** — In Railway dashboard, set: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_REPORT` (one-time price ID), `STRIPE_PRICE_MONITORING` (recurring price ID). All four are required.
- [ ] **Configure Stripe webhook** — In Stripe dashboard → Developers → Webhooks: add endpoint `https://assay.tools/v1/webhooks/stripe`, subscribe to events: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET` env var.

**Stripe code fixes (sessions can claim)**:
- [x] **Fix webhook signature bypass** — Require STRIPE_WEBHOOK_SECRET, return 503 if missing. No more dev-mode bypass. (2026-03-05)
- [x] **Fix orphan order creation** — Use db.flush()/rollback pattern: get order ID for success URL, only commit after Stripe session succeeds (2026-03-05)
- [x] **Fix buyReport() JS event handling** — Pass event as explicit parameter instead of implicit global (2026-03-05)
- [x] **Add Stripe vars to .env.example** — Added STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_REPORT, STRIPE_PRICE_MONITORING (2026-03-05)
- [x] **Email sending infrastructure** — Resend integrated (2026-03-07). `src/assay/notifications/email.py` with order confirmations + report delivery (PDF/markdown attachments). Resend for transactional outbound, Migadu stays for inbound/conversational. Domain verified (DKIM/SPF/MX on `send` subdomain, no conflict with Migadu). API key in GCP Secret Manager. **Remaining**: Set RESEND_API_KEY in Railway env vars.

### Phase 2: Monitoring Product (enables $3/mo recurring revenue)

- [ ] **User accounts** — Registration + login for package monitoring subscribers. Email/password or magic link auth. Store in DB. JWT or session-based. **Files**: new `src/assay/models/user.py`, new `src/assay/api/auth_routes.py`, new templates for login/register
- [ ] **Package monitoring subscriptions** — Authenticated users can subscribe to packages ($3/mo each via Stripe). Dashboard showing subscribed packages, current scores, trends. **Files**: new `src/assay/models/subscription.py`, new `src/assay/api/subscription_routes.py`, new `templates/dashboard.html`
- [x] **Score history tracking** — ScoreSnapshot model + /v1/packages/{id}/score-history API + auto-snapshot in loader, 5 tests (2026-03-04)
- [x] **Score change email notifications** — `send_score_change_alert()` in notifications/email.py, wired into loader.py. Captures old scores, compares after commit, emails active monitoring subscribers on any change. Deduplicates by email. (2026-03-07)
- [ ] **Agent score change notifications** — Webhook subscription endpoint for agents to register callbacks for score changes. Gated behind paid monitoring subscription ($3/mo). Options: (1) `POST /v1/webhooks/subscribe` with package_id + callback_url, requires active Stripe subscription, (2) SSE on MCP server for real-time push, (3) document `/v1/packages/updated-since` as free polling alternative. Webhook payloads include old/new scores + deltas. **Files**: new `src/assay/api/webhook_routes.py`, new `src/assay/models/webhook.py`, update `src/assay/evaluation/loader.py` to dispatch webhook calls on score change

### Phase 3: Data Quality & Automation

- [ ] **Score backfill** — 500+ existing evaluations use old schema with only top-level security_score and no sub-component breakdown or reliability_score. Re-evaluate to populate all 14 sub-components. Can be batched via the evaluation skill
- [x] **Automated re-evaluation pipeline** — Weekly GitHub Action + check_stale.py script, creates/updates issue with stale packages (2026-03-04)
- [x] **Data freshness dashboard** — Admin view showing evaluation coverage, staleness distribution, queue depth, and re-evaluation velocity

### Overnight Evaluation Sessions (PAUSED 2026-03-07)

**Status**: Both launchd jobs unloaded. Plist files still on disk for re-enabling.

**What they are**:
- `com.assay.session1.plist` — runs at 22:31, prompt: `scripts/session-1-business.md` (Sonnet)
- `com.assay.session2.plist` — runs at 03:32, prompt: `scripts/session-2-polish.md` (Sonnet)
- Both use `scripts/run-session.sh` to launch a Claude Code session with a prompt file

**Why paused**:
- `run-session.sh` does a broad `git add .` which sweeps in unrelated uncommitted work from interactive sessions (e.g., the Resend integration got committed inside an evaluation batch commit `294e44e`)
- This creates messy commit history and can push half-finished work to production

**Before re-enabling, fix**:
- [ ] `run-session.sh` must only stage evaluation-related files (`git add evaluations/ logs/` or explicit paths), NOT `git add .`
- [ ] Consider running in a worktree to fully isolate overnight work from interactive sessions
- [ ] Review both prompt files (`session-1-business.md`, `session-2-polish.md`) for scope creep

**To re-enable**: `launchctl load ~/Library/LaunchAgents/com.assay.session1.plist` (and session2)

---

### Automated Discovery System (continuous package pipeline)

**Current state**: 7 sources (was 4), GitHub auth support, expanded search queries, ~7,000 packages. Needs scheduled runs and quality scoring.

**Infrastructure**:
- [x] **Add GitHub token to discovery** — GITHUB_TOKEN env var support in GitHubSource and OpenClawSource. 5,000 req/hr authenticated vs 60. **AJ**: create GitHub PAT (fine-grained, read-only public repos) and add to Railway env vars. (2026-03-05)
- [x] **Scheduled discovery runs** — GitHub Action twice daily (06:00/18:00 UTC) with manual trigger, configurable source/limit (2026-03-05)
- [x] **Discovery run logging** — JSON lines to logs/discovery/runs.jsonl with timestamp, sources, counts, totals (2026-03-05)

**New GitHub search queries**:
- [x] **Expand GitHub MCP search** — 7 queries (was 3): topic:model-context-protocol, @modelcontextprotocol/sdk in:file, language-specific path searches (2026-03-05)
- [x] **GitHub skill discovery** — 9 queries (was 4): claude-code-skill, ai-agent-tool, langchain-tool, crewai-tool, tool_use in readme (2026-03-05)

**New registry sources**:
- [x] **Smithery.ai registry** — SmitherySource added, requires SMITHERY_TOKEN. AJ: create token at smithery.ai (2026-03-05)
- [ ] **mcp.run registry** — Another MCP hub. Same approach: API if available, scrape if not. **Files**: new `src/assay/evaluation/sources/mcprun.py`
- [ ] **Glama.ai MCP directory** — Glama maintains an MCP server directory. Check for API/scraping options. **Files**: new `src/assay/evaluation/sources/glama.py`
- [x] **npm/PyPI search** — NpmSource (4 search queries) + PyPISource (simple index filter by mcp-* prefix) (2026-03-05)
- [x] **Awesome list expansion** — 5 repos (was 3): added wong2/awesome-mcp-servers, appcypher/awesome-mcp-servers (2026-03-05)

**Quality & dedup**:
- [ ] **Cross-source deduplication improvements** — Current dedup is by normalized repo URL and slug. Add: npm package name matching, PyPI package name matching, and fuzzy name matching for packages that appear in multiple registries under slightly different names
- [x] **Discovery quality scoring** — Priority now uses stars + recent activity (high/medium/low tiers) (2026-03-05)

### Business Heartbeat & Orchestration System

**Purpose**: The business manager (AJ or an agent acting on AJ's behalf) needs continuous situational awareness of the business. The heartbeat fires on a regular cadence, checks for needed actions across all business functions, and routes them to the appropriate handler.

- [x] **Heartbeat scheduler design** — CLI runner `python -m assay.heartbeat` with text/json output, exit codes (0=healthy, 1=warnings, 2=critical). Run via cron/launchd/GitHub Action. (2026-03-05)
- [ ] **Business metrics checks** — Heartbeat check: query Stripe for new orders/revenue, check for pending webhook failures, monitor order fulfillment status (any orders stuck in "pending" too long?). Alert if: revenue event, failed payment, stuck order. **Files**: new `src/assay/heartbeat/revenue.py`
- [x] **Site health checks** — Endpoint status, response time, key page checks, SSL cert expiry monitoring (2026-03-05)
- [x] **Data pipeline checks** — Evaluation coverage, staleness distribution, velocity tracking (2026-03-05)
- [x] **Feedback & support checks** — Recent submissions count, subscriber count (2026-03-05)
- [ ] **Competitor & market checks** — Heartbeat check (less frequent, maybe daily): check if new MCP registries have appeared, monitor key competitor sites for changes, check GitHub trending for MCP-related repos. Alert if: new competitor detected, significant market shift. **Files**: new `src/assay/heartbeat/market.py`
- [x] **Orchestrator** — Central dispatcher with combined alert collection, severity sorting, text/json output (2026-03-05)
- [x] **Business dashboard endpoint** — `GET /admin/dashboard` returning combined health + revenue + alerts JSON, protected by admin key (2026-03-05)

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
