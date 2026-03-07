# Assay — Goal & Success Criteria

**Domain**: assay.tools
**Tagline**: The quality layer for agentic software.
**Last Updated**: 2026-03-07

---

## Mission

Assay rates software packages on agent-friendliness, security, and reliability — giving both humans and AI agents the quality signal they need to choose tools. The evaluation pipeline is itself agentic: agents discover, test, and score packages autonomously.

The business proves three things:
1. **The data is valuable** — structured ratings that agents can query to select tools
2. **The pipeline is agentic** — agents can autonomously evaluate packages at scale
3. **The product generates revenue** — paid reports, monitoring, and certifications

### Core Philosophy: Agents Are First-Class Citizens

Assay was built for agents first, humans second. Every interface, data format, and design decision treats AI agents as a primary audience — not an afterthought.

**What this means in practice:**
- **Agents discover tools through Assay** — an agent can query the API or MCP server to find the best package for a task, filtered by score, category, or capability
- **Agents recommend tools to humans** — using Assay's structured ratings and evidence-based scoring, agents can make informed recommendations backed by solid data
- **Agents consume Assay data natively** — JSON API, MCP server, OpenAPI spec, llms.txt, CLI with JSON output — all designed for programmatic consumption
- **Agents evaluate packages autonomously** — the evaluation pipeline itself is agentic, proving the model end-to-end
- **Humans get the same quality** — the web frontend, PDF reports, and human-readable formats are built on top of the same data, not a separate track

The core use case: a developer asks their agent to find the best tool for a job. The agent queries Assay, evaluates options across AF/Security/Reliability dimensions, and recommends tools with confidence — because the scores are earned through real evaluation, not marketing copy.

---

## Current Goal: First Revenue

MVP is complete. The product is live, deployed, and can accept payments. The current goal is to close the loop: **get real money from a real customer**.

### What that requires (in order)
1. LLC approval + EIN + business bank account (in progress)
2. Stripe live keys in production
3. Soft launch to trusted testers (Daniel Miessler + 5-10 from AJ's network)
4. Public launch (HN, Reddit, Discord, Product Hunt)
5. First paid report or monitoring subscription

### How we'll know it worked
- At least 1 paid transaction through Stripe
- Positive signal from beta testers on scoring credibility
- Organic traffic from at least 2 channels post-launch

---

## Success Criteria

### MVP (COMPLETE)

All items below are built, tested, and deployed to production.

- [x] Database schema with full package record structure (Postgres on Railway)
- [x] 6,400+ packages evaluated with AF/Security/Reliability scores
- [x] REST API with filter/search/compare/change-feed/category-leaderboards
- [x] Assay's own MCP server (4 tools: find, get, compare, list categories)
- [x] Full web frontend: categories, search, package detail, comparison, methodology
- [x] Evaluation pipeline: 7-source discovery, 3-tier strategic scheduler, evidence-banded rubric v2
- [x] Deploy-ready on Railway with auto-deploy from main
- [x] Comparison endpoint (`/v1/compare?ids=a,b,c`)
- [x] Change feed endpoint (`/v1/packages/updated-since`)
- [x] CLI tool: `assay check/compare/stale` with ASCII + JSON output
- [x] Automated re-evaluation pipeline (strategic scheduler with 30-day freshness target)
- [x] Score history / trend tracking (ScoreSnapshot model)
- [x] OpenAPI spec auto-generated at /openapi.json
- [x] llms.txt at assay.tools/llms.txt
- [x] CI/CD pipeline (GitHub Actions: lint + test on push/PR)

### Revenue Infrastructure (COMPLETE — awaiting Stripe live keys)

- [x] Stripe Checkout integration (4 products: Brief $3, Report $99, Monitoring $3/mo, Support custom)
- [x] Webhook handler with signature verification
- [x] Post-payment report generation (Claude Opus narratives, branded PDF + markdown)
- [x] Report caching (generate once per evaluation cycle)
- [x] Transactional email via Resend (order confirmations, report delivery with attachments)
- [x] Admin bookkeeping (/admin/transactions, /admin/revenue)
- [x] GitHub Action for CI score checks
- [x] Embeddable score badges and comparison widgets

### Post-MVP (NOT YET BUILT)

- [ ] User accounts (for monitoring subscriptions)
- [ ] Package monitoring dashboard (subscriber view of tracked packages)
- [x] Score change email notifications
- [ ] Privacy-first analytics (Umami or Plausible)
- [ ] Certified Agent-Ready program ($299/mo)
- [ ] Community evaluation network (external contributors)

---

## Revenue Model

| Product | Price | Status |
|---------|-------|--------|
| Directory + API | Free (100 calls/day) | Live |
| Package Brief | $3 one-time | Built, awaiting Stripe live |
| Full Evaluation Report | $99 one-time | Built, awaiting Stripe live |
| Package Monitoring | $3/mo per package | Built, awaiting Stripe live |
| Support the Mission | Custom (min $1) | Built, awaiting Stripe live |
| Certified Agent-Ready | $299/mo | Future (Q3+) |

**Break-even at $23/mo operating cost**: 1 report sale every ~4 months, or 8 monitored packages.
