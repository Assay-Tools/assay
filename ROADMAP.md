# Assay Roadmap

**Last Updated**: 2026-03-07

What's done, what's next, and what's deferred. See WORKBOARD.md for tactical task tracking.

---

## What's Built (as of 2026-03-07)

Everything below is live at assay.tools and deployed on Railway.

**Core Product**: Full directory (~6,900 packages, ~6,400 evaluated), 3-dimension scoring (AF, Security, Reliability), 16 canonical categories, package detail pages with sub-component breakdown, radar charts, staleness badges, side-by-side comparison.

**API & Integrations**: REST API with filter/search/compare/change-feed/category-leaderboards, MCP server (4 tools), CLI (`assay check/compare/stale`), GitHub Action for CI score checks, embeddable badges + comparison widgets, RSS feed, `llms.txt`, OpenAPI spec.

**Revenue Infrastructure**: Stripe Checkout (sandbox — 4 products: Brief $3, Report $99, Monitoring $3/mo, Support custom), webhook handler, post-payment PDF+markdown report generation (Claude Opus narratives), report caching, order tracking, admin bookkeeping.

**Email**: Resend for transactional outbound (order confirmations, report delivery with attachments). Migadu for inbound/conversational (mailboxes, IMAP, MCP server access).

**Evaluation Pipeline**: 7-source discovery (GitHub, Smithery, npm, PyPI, awesome lists), strategic 3-tier scheduler (flagged → unevaluated → stale), evidence-banded rubric v2 with 14 sub-components, community submission API with GitHub OAuth + trust tiers.

**Website & UX**: Landing page, developer docs, methodology page, Terms/Privacy (draft), about, feedback form, email subscriber capture, report-inaccuracy links, SEO (JSON-LD, OG, sitemap).

**Infrastructure**: 168 tests, CI/CD (GitHub Actions), rate limiting, admin/submitter key separation, security headers, CORS, score history tracking, data freshness dashboard, API usage analytics.

---

## Current Phase: Pre-Launch

### AJ Must Do (blocking)

1. **LLC approval** — Business 34 LLC filed 2026-03-05, awaiting IL Secretary of State (~10 business days). Then: EIN → business bank account → "Assay Tools" DBA.
2. **Stripe live keys** — Swap test keys for live once bank account is ready. Set 4 env vars in Railway.
3. **Review legal docs** — ToS + Privacy Policy are drafts. Lawyer review before accepting real money.

### Soft Launch (next)

4. **Daniel Miessler outreach** — Personal DM for methodology gut-check before going public.
5. **5-10 beta testers** — Personal invites from AJ's network with specific questions.
6. **Beta fixes sprint** — Act on feedback before public launch.

### Public Launch (after soft launch feedback)

7. **Blog post** — "How We Rate 7,000 APIs for Agent-Readiness" on Dev.to (publish before HN).
8. **HN submission** — Show HN, target Tuesday 10-11am ET. One-shot weapon — don't waste it.
9. **Reddit rollout** — r/SideProject, r/selfhosted, r/programming, r/machinelearning (staggered over a week).
10. **Discord seeding** — Fabric, Anthropic, LangChain communities.
11. **Product Hunt** — After HN/Reddit dust settles.

---

## Near-Term Roadmap (post-launch)

### Analytics & Tracking
- [ ] Choose and deploy privacy-first analytics (Umami self-hosted or Plausible)
- [ ] Add analytics script to base template
- [ ] Define conversion goals (report purchase, email signup, API docs visit, badge copy)
- [ ] Privacy-respecting consent mechanism for enhanced tracking

### Phase 2: Monitoring Product ($3/mo recurring)
- [ ] User accounts (registration + login, email/password or magic link)
- [ ] Package monitoring subscriptions (per-package via Stripe)
- [ ] Score change notifications (email via Resend when monitored package scores change)
- [ ] Subscriber dashboard (subscribed packages, current scores, trends)

### Data Quality
- [ ] Score backfill — re-evaluate 500+ old packages missing sub-component breakdown
- [ ] Evaluation confidence indicator (single eval vs cross-validated vs high confidence)
- [ ] Fix overnight evaluation sessions — scope `git add` to evaluation files only, consider worktrees, then re-enable (see WORKBOARD.md for details)

---

## Medium-Term (Q2-Q3 2026)

### Strategic Growth
- [ ] Target companies, not just individuals — reframe $99 report as competitive analysis for DevRel teams
- [ ] Partnership: Smithery.ai — MCP directory + quality layer
- [ ] Partnership: Agent frameworks (LangChain, CrewAI, AutoGen, Semantic Kernel)
- [ ] Methodology Advisory Board (Daniel Miessler first)
- [ ] Content calendar + newsletter (monthly "Top Movers", quarterly ecosystem reports)
- [ ] LinkedIn thought leadership

### Discovery Expansion
- [ ] mcp.run registry source
- [ ] Glama.ai MCP directory source
- [ ] Cross-source deduplication improvements (npm/PyPI name matching, fuzzy matching)

### Business Operations
- [ ] Business metrics heartbeat checks (Stripe revenue, webhook failures, stuck orders)
- [ ] Competitor & market monitoring heartbeat
- [ ] Launch effectiveness dashboard

---

## Long-Term (Q3+ 2026)

- [ ] Certified Agent-Ready program ($299/mo) — verified badge, priority re-evaluations, competitive reports
- [ ] Community evaluation network — external contributors, reputation system, review queue
- [ ] Live API testing — actually call package APIs to verify error formats, latency, auth
- [ ] Multi-source context gathering — npm/PyPI metadata, changelog parsing, status page scraping
- [ ] Per-engine calibration offsets if systematic scoring bias detected
- [ ] Self-evaluation detection via domain matching
