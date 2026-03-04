# Assay — Business Model & Operating Philosophy

**Last Updated**: 2026-03-04

---

## Operating Philosophy: Agentic-First Business

Assay is designed to be an **agentic business** — one where AI agents are not just the product but the operators. The human founder (AJ) provides strategic direction, financial gatekeeping, and relationship building. Agents handle analysis, research, content generation, evaluation, prospecting, and operational execution.

### Principles

1. **Agents drive the business forward.** Claude is empowered to research markets, evaluate packages, generate reports, draft communications, convene councils of agents for debate, and come to AJ with solid, well-reasoned recommendations. Don't wait to be asked — identify opportunities and propose action.

2. **Bootstrap-first.** Assay has no external capital. All AI work runs on AJ's existing Claude subscription (not API calls) until revenue covers costs. Every decision should optimize for low cost and high leverage.

3. **Revenue before perfection.** Ship knowledge products, run prospecting, and generate revenue with existing data. Polish and scale after cash flow is established.

4. **AJ is the financial gatekeeper.** Agents cannot spend money without approval. When a spend is needed, present the case with expected ROI. This constraint will relax as revenue grows.

5. **Experiment and learn.** This is uncharted territory. Track what works, document what doesn't, and iterate fast.

### Agent Authorities (Current)

| Authority | Status | Notes |
|-----------|--------|-------|
| Run evaluations | Autonomous | Use existing subscription, no API costs |
| Generate reports and content | Autonomous | Core business activity |
| Draft emails and communications | Autonomous | AJ reviews before sending |
| Research markets and competitors | Autonomous | |
| Propose pricing changes | Recommend | AJ approves |
| Commit and push code | Autonomous | Standard dev workflow |
| Deploy to production | Autonomous | Via git push to main (auto-deploy) |
| Spend money | Blocked | AJ approves all expenditures |
| Send emails to external parties | Blocked | AJ approves outbound comms |
| Modify business strategy | Recommend | AJ approves major pivots |

These authorities will expand as trust and revenue grow.

---

## Revenue Streams

### 1. Platform Access

#### Free Tier — $0

For agents and humans exploring the agentic software landscape.

- Browse full directory, read all scores, search and filter
- API access: **100 calls/day** (enough for personal use, not enough to scrape)
- MCP server access (same rate limit)
- Web UI with no restrictions

**Rationale**: The directory is the trust engine. Paywalling it would undermine credibility. Rate limits prevent abuse while keeping the platform open to everyone.

#### Package Monitoring (Pro) — $3/month per package

For package owners, developers, and maintainers who want to stay on top of their scores.

- **Score change notifications** — email alert when your package's AF Score changes, with explanation of what changed and why
- **Score history tracking** — trend data showing how your score has moved over time
- **Monthly mini-report** — automated summary of your package's standing in its category
- **Additional API headroom** — 200 calls/day (vs 100 free)
- **Per-package pricing** — pay only for the packages you care about

**Pricing rationale**: $3/mo is a slam dunk. One package = cost of a coffee. A maintainer with 10 packages = $30/mo, still very reasonable. Low friction to start, scales naturally with the customer's footprint, and every subscriber directly supports the platform.

**Examples**:
- Solo dev with 1 MCP server: $3/mo
- Small shop with 5 packages: $15/mo
- Active maintainer with 15 packages: $45/mo

#### Certified Agent-Ready — $299/month (Future, not built yet)

For organizations that want third-party validation of their agent-readiness.

- Embeddable verified score widget for their own docs/site
- Unlimited priority re-evaluations (every release gets re-scored)
- Monthly competitive category report
- Improvement consulting (agent-generated, prioritized roadmap)
- Featured placement in Assay directory
- Use of "Certified Agent-Ready" mark in marketing materials
- Score API endpoint for displaying their score dynamically

**Status**: Deferred to Q3/Q4 2026. The badge only has value once Assay has enough brand recognition that certification means something. Build the brand first with free content and $99 reports, then activate this tier.

**Rationale**: Free tier builds trust and distribution. Pro tier generates sustainable recurring revenue at low friction. Certified tier is a future premium offering that requires brand equity to justify.

### 2. Knowledge Products — Package Evaluation Reports

One-time revenue from detailed, actionable reports delivered to package owners/maintainers.

| Product | Price | Audience | What They Get |
|---------|-------|----------|---------------|
| **Package Evaluation Report** | $99/one-time | Package maintainers | Full AF score breakdown, sub-component analysis, specific improvement recommendations, competitive positioning within category, agent-readiness roadmap |

**How it works**:
- Assay already has evaluation data for 2,456+ packages
- The report adds personalized narrative, prioritized recommendations, and competitive context
- Agent-generated, human-reviewed before delivery
- Marginal cost is near zero (data exists, report generation is agentic)

**Upsell path**: Report recipients become natural candidates for $3/mo monitoring (track their improvements) and eventually Certified ($299/mo) once that tier launches.

### 3. Knowledge Products — Quarterly Ecosystem Reports

Free knowledge products that build authority and drive awareness.

| Product | Price | Audience | Purpose |
|---------|-------|----------|---------|
| **Quarterly State of Agentic Software** | Free (email capture) | Community, developers, vendors, press | Thought leadership, lead generation, brand building |

**Content**:
- Ecosystem growth metrics (packages discovered, evaluated, score trends)
- Category-level insights (which categories are improving, which are stagnant)
- Top movers (packages with biggest score changes)
- Emerging categories and trends
- Notable findings (common gotchas, security patterns, auth complexity trends)

**Distribution strategy**:
- Free download with email capture (builds prospect list)
- Every package mentioned = warm lead for $99 report
- Shareable format (PDF + web version) for social distribution
- Positions Assay as the authoritative voice on agentic software quality

**Cadence**: Quarterly (Q1 = Jan-Mar, published early April)

---

## Prospecting & Sales Strategy

### Package Evaluation Report ($99) — Prospecting Funnel

1. **Lead source**: Assay's own evaluation database (2,456+ evaluated packages)
2. **Warm outreach**: Email package maintainers with a teaser — "We evaluated [package]. Here's your AF Score: [X/100]. Want the full breakdown with improvement recommendations?"
3. **Delivery**: Agent-generated report, AJ reviews, delivered via email as PDF
4. **Upsell**: Offer $3/mo monitoring to track improvements over time

### Quarterly Report — Lead Gen Funnel

1. **Publish report** (free, email-gated or ungated)
2. **Every package mentioned** gets a notification email: "Your package was featured in our Q1 report"
3. **CTA in notification**: "Want your detailed evaluation? $99 for the full report"
4. **Social amplification**: Share key findings on social media, dev communities

### Priority Targets for Prospecting

Focus outreach on packages that are:
- **High-profile** (many GitHub stars, well-known in community)
- **Medium AF scores** (55-75 range — good enough to care, room to improve)
- **Active development** (recent commits, responsive maintainers)
- **In growing categories** (AI/ML tools, MCP servers, cloud infrastructure)

---

## Cost Structure

### Current (Bootstrap Phase)

| Cost | Amount | Notes |
|------|--------|-------|
| Claude subscription | $20/mo (current) | Primary compute for all agentic work |
| Railway hosting | Free tier | May need upgrade as traffic grows |
| Domain (assay.tools) | ~$30/yr | Porkbun |
| Cloudflare DNS | Free | |
| Gmail (assaytools@gmail.com) | Free | Business email via forwarding |
| **Total** | **~$23/mo** | |

### Near-Term Upgrades (When Revenue Supports)

| Cost | Amount | Trigger |
|------|--------|---------|
| Claude Max 20 | $200/mo | When bottleneck impacts revenue generation |
| Railway paid tier | ~$5-20/mo | When free tier limits hit |
| Email service (Resend/Postmark) | ~$10-20/mo | When outbound volume exceeds Gmail limits |

### Break-Even Targets

- **Current costs ($23/mo)**: 1 report sale every ~4 months, or 8 monitored packages
- **With Claude Max ($223/mo)**: 3 reports/month, or 2 reports + 25 monitored packages
- **Comfortable operating margin ($500/mo revenue)**: 4 reports + 30 monitored packages

---

## Metrics to Track

### Business Health
- Monthly revenue (by stream)
- Report sales count and conversion rate
- Subscriber count by tier
- Email list size (from quarterly report)
- Outbound prospecting: sent → opened → purchased

### Product Health
- Total packages evaluated
- Evaluation freshness (% evaluated within 90 days)
- API query volume
- Website traffic and engagement
- MCP server usage

### Agentic Operations
- Reports generated per session
- Evaluations completed per session
- Prospecting emails drafted per session
- Time from evaluation to report delivery

---

## Roadmap Alignment

**Q1 2026 (Current — March)**:
- [x] SSL and production deployment
- [ ] Q1 ecosystem report template + first report
- [ ] Package evaluation report template + first batch
- [ ] Prospecting routine (first outreach wave)
- [ ] Email handling infrastructure

**Q2 2026**:
- Payment processing (Stripe)
- Package Monitoring (Pro) tier activation ($3/mo per package)
- Automated re-evaluation pipeline
- Second quarterly report
- Scale prospecting based on Q1 learnings

**Q3+ 2026**:
- Certified Agent-Ready tier activation (requires brand equity)
- Community contributions (distributed evaluation network)
- CLI tool
- API rate limiting infrastructure
