# Assay — Project Status

**Last Updated**: 2026-03-05 03:10
**URL**: https://assay.tools
**Repo**: ~/git/assay (github.com/Assay-Tools/assay)
**Hosting**: Railway (auto-deploys from main)
**DB**: Postgres via Railway (public proxy: interchange.proxy.rlwy.net:42133)

---

## Current State: Launch-Ready (pending AJ actions)

All technical work for Phase 0 and Phase 1 is complete. The product can accept payments, deliver reports, and handle public traffic. What remains is human-only tasks.

### By the Numbers

| Metric | Value |
|--------|-------|
| Packages tracked | ~6,954 |
| Evaluation JSONs | 3,155 files |
| Packages evaluated (with AF scores) | ~2,456+ |
| MCP servers tracked | ~300 |
| Avg AF Score | ~61 |
| Tests | 167 passing |
| Commits (Mar 4-5 alone) | 100+ |
| Monthly operating cost | ~$23 |

### What's Built and Working

**Core Product**:
- Full directory with search, filters, pagination, 16 canonical categories
- 3-dimension scoring: Agent Friendliness (AF), Security, Reliability
- Package detail pages with sub-component breakdown, radar chart, staleness badges
- Side-by-side package comparison (web + API)
- Evaluation queue for community contributors

**API & Integrations**:
- REST API: full CRUD, filtering by score dimensions, change feed, category leaderboards
- MCP server (4 tools: find, get, compare, list categories)
- CLI tool: `assay check/compare/stale` with ASCII + JSON output
- GitHub Action for CI score checks
- Embeddable score badges (`/badge/{id}.svg`)
- Embeddable comparison widgets (`/embed/compare?ids=a,b`)
- RSS feed (`/feed.xml`)
- `llms.txt` and `llms-full.txt` for LLM crawlers
- OpenAPI spec with full documentation

**Revenue Infrastructure**:
- Stripe Checkout for $99 one-time report purchases
- Stripe webhook handler (checkout.session.completed, subscription events)
- Post-payment PDF report generation + download endpoint
- "Buy Full Report — $99" button on package detail pages
- Admin bookkeeping: /admin/transactions (JSON/CSV), /admin/revenue
- Order model with status tracking

**Website & UX**:
- Landing page with hero, search, top-rated, recently evaluated, category grid
- Developer docs page (`/developers`) with API examples, MCP config, rate limits
- Scoring methodology page (`/methodology`) with full weight disclosure
- Terms of Service and Privacy Policy (DRAFT — needs lawyer review)
- About page with team attribution, disclaimer, dispute process
- Feedback collection page (`/feedback`) with structured form
- Email subscriber capture on homepage
- "Report inaccuracy" links on every package page

**Infrastructure**:
- 167 tests (all passing), CI/CD via GitHub Actions (lint + test)
- Rate limiting: 100/day API, 20/day submissions
- Admin/submitter API key separation
- Score history tracking (ScoreSnapshot model)
- Automated stale evaluation detection (weekly GitHub Action)
- Data freshness admin dashboard
- Security headers, CORS properly configured, LIKE sanitization, sort whitelisting
- SEO: JSON-LD structured data, OG tags, sitemap.xml, meta descriptions

---

## Critical Path — What Happens Next

### AJ Must Do (no one else can)

**1. Form LLC + EIN (THIS WEEK)**
- File LLC in home state ($50-200 filing fee)
- Get EIN from IRS: https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online (free, immediate)
- Open business bank account
- WHY: Zero liability protection right now. Every legal claim reaches personal assets. Must complete before Stripe goes live or any outbound prospecting.

**2. Rotate Production Credentials (THIS WEEK)**
- The `.secrets` file on disk contains live production DB password on a publicly-accessible Postgres proxy
- Go to Railway dashboard → rotate DB password
- Delete `~/git/assay/.secrets` from disk
- Set all secrets as Railway environment variables only
- Also rotate: Railway deploy token, Gmail app password

**3. Pick Email Sending Service (THIS WEEK)**
- Recommendation: Resend (developer-friendly, generous free tier)
- Alternative: Postmark
- Create account, get API key, set as Railway env var
- Needed for: report delivery emails, payment confirmations, future notifications

**4. Review Legal Docs**
- ToS at /terms and Privacy Policy at /privacy are DRAFTS
- Have a lawyer review before accepting real money
- Key areas: defamation protection (scores as editorial opinions), limitation of liability, GDPR/CCPA compliance

**5. Message Daniel Miessler (THIS WEEK)**
- Personal DM, not public
- Suggested framing: "I built a rating system for MCP servers and APIs. Fabric is in the dataset. Before I go public, would you spend 15 minutes poking around assay.tools and tell me: (1) Does the scoring feel credible? (2) Anything that would make you distrust the ratings? (3) Would you use this yourself?"
- Goal: credible practitioner gut-check before going wide

**6. Identify 5-10 Beta Testers (NEXT WEEK)**
- From your network: security, AI, DevOps people
- Mix of: MCP server builders, agent framework users, API design people, security folks
- Send personal invites with specific questions about scoring credibility and willingness to pay

### After Soft Launch Feedback (2-3 weeks out)

**7. Beta Fixes Sprint**
- Act on feedback from Daniel and beta testers
- Fix credibility issues, UX problems, methodology concerns

**8. Public Launch Week** (target: a Tuesday, 10-11am ET)
- Monday: Post to r/SideProject (warm-up)
- Tuesday: Show HN — "Show HN: Assay — We rated 2,400+ APIs and MCP servers for agent-readiness"
- Wednesday: r/selfhosted (MCP angle)
- Thursday: Anthropic Discord, Fabric Discord, LangChain Discord
- Friday: r/programming (link to methodology blog post)
- Following week: r/LocalLLaMA, r/MachineLearning, LinkedIn, Product Hunt

**9. Publish Blog Post BEFORE HN**
- "How We Rate 7,000 APIs for Agent-Readiness" on Dev.to
- Establishes methodology credibility that HN commenters can reference
- Drives organic SEO traffic independently

---

## Remaining Workboard Items (26 total)

### Immediate / AJ-only (4 items)
- Form LLC + EIN
- Rotate production credentials
- Pick email sending service
- Review ToS/Privacy with lawyer

### Soft Launch — AJ-driven (3 items)
- Daniel Miessler outreach
- Beta tester selection + invites
- Beta fixes sprint

### Public Launch — AJ-driven (5 items)
- HN submission
- Reddit posts (4 subs, staggered)
- Discord seeding (Fabric, Anthropic, LangChain)
- Product Hunt
- Dev.to blog post

### Phase 2 Product (3 items — can wait)
- User accounts (for monitoring subscribers)
- Package monitoring subscriptions ($3/mo)
- Score change notifications

### Strategy & Growth (7 items)
- Target companies not just individuals (reframe $99 as competitive analysis for DevRel)
- Partnership: Smithery.ai (MCP directory + quality layer)
- Partnership: Agent frameworks (LangChain, CrewAI, AutoGen)
- Methodology Advisory Board (Daniel first)
- Seed modelcontextprotocol/servers GitHub discussions
- LinkedIn presence
- Content calendar + newsletter

### Future (4 items)
- Score backfill (old evals missing sub-components)
- Email sending infrastructure
- Certified Agent-Ready program ($299/mo)
- Community evaluation network

---

## Key Strategic Insights (from multi-angle review, 2026-03-04)

1. **The $23/mo cost is a superpower** — no burn clock. Use it to build credibility before monetizing.
2. **Cold-emailing individual maintainers will convert near-zero.** Better early customers are companies with API products (DevRel teams) and agent framework builders.
3. **The category "agent-readiness" doesn't exist yet.** Assay must create it AND win it. First-mover advantage is real but fragile.
4. **The GitHub Action and embeddable badges are the highest-leverage growth mechanics.** Every README embed is a permanent backlink.
5. **Publish methodology openly** (like OpenSSF Scorecard). Transparency builds trust for an unknown brand.
6. **Smithery.ai is the natural first partnership** — they're the MCP directory, Assay is the quality layer.
7. **HN is a one-shot weapon.** Don't post until methodology blog is live, site is polished, and beta feedback is incorporated.

---

## Revenue Model Summary

| Product | Price | Status |
|---------|-------|--------|
| Directory + API | Free (100 calls/day) | Live |
| Package Evaluation Report | $99 one-time | Stripe + delivery built |
| Package Monitoring (Pro) | $3/mo per package | Needs user accounts |
| Certified Agent-Ready | $299/mo | Future (Q3+, needs brand equity) |
| Consulting/competitive analysis | $499-999 | Suggested by business review, not yet built |

**Break-even at current costs ($23/mo)**: 1 report sale every ~4 months, or 8 monitored packages.
