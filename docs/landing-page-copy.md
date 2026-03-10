# Landing Page Copy — assay.tools

> Working document for web developer implementation.
> Tagline: **The quality layer for agentic software.**

---

## Hero Section

### Headline
**The quality layer for agentic software.**

### Subheadline
17,977 MCP servers. Zero independent quality ratings. Until now.

Assay scores software packages — MCP servers, APIs, SDKs — on how well they actually work with AI agents. Pre-computed. Machine-readable. No guesswork at runtime.

### Hero CTA Row
- **[Browse Ratings →](/packages)** — Free, no account required
- **[Try the API →](/api/v1/packages)** — Agent-to-agent, JSON out of the box
- **[Get Certified →](/about)** — For vendors signaling agent-readiness

---

## Stats / Credibility Bar

| Stat | Value |
|------|-------|
| Packages evaluated | 4,039+ |
| Packages cataloged | 7,959+ |
| Categories covered | 16 |
| Average AF Score | 62.4 / 100 |
| MCP servers tracked | 750+ |
| MCP servers in the wild | 17,977+ |
| Independent quality ratings before Assay | 0 |

> Comparable to what Socket.dev did for npm security in 2022 — but for agent-readiness.

---

## Value Props by Audience

### For AI Agents and Agent Operators

> Your agent shouldn't have to learn the hard way that a tool breaks on edge cases.

- **Runtime tool selection, solved.** Query the Assay MCP server or REST API mid-execution — get ranked package recommendations without spinning up an LLM.
- **Pre-computed scores, sub-millisecond reads.** No inference at query time. Ratings live in a database; your agent gets the answer fast.
- **Gotchas and avoid-when conditions, baked in.** Assay surfaces known failure modes and edge cases so your agent can route around them before they cause problems.
- **Auth complexity scores.** Know whether a tool requires OAuth flows, API keys, or nothing — before your agent tries to call it.

**CTA:** [Query the API →](/api/v1/packages) — OpenAPI spec available, MCP server ready to mount

---

### For Developers Building Agents

> Stop discovering that a popular package is undocumented garbage at 2am.

- **Curated ratings across 63 categories.** Browse by use case — file systems, memory, databases, communication tools, and more.
- **AF Score at a glance.** One number (0–100) that summarizes MCP quality, documentation accuracy, error message usefulness, security posture, and auth complexity.
- **Documentation accuracy scores.** Know whether a tool's docs match its actual behavior — a surprisingly rare quality.
- **Error quality ratings.** Find packages that return useful errors when things go wrong, not cryptic stack traces.

**CTA:** [Browse Ratings →](/packages) — Free, no login required

---

### For Software Vendors

> "Agent-ready" is easy to claim. Hard to prove. Now there's a third-party standard.

- **Certified Agent-Ready badge.** Display independent verification that your package meets quality thresholds for production agent use.
- **Detailed score breakdown.** See exactly how you score on MCP quality, documentation accuracy, error messages, security, and auth complexity — and what to fix.
- **Competitive benchmarking.** Compare your scores against similar tools in your category.
- **Signal to a new distribution channel.** Agent operators are choosing tools programmatically. Being discoverable and well-scored in Assay puts you in front of that pipeline.

**CTA:** [Get Certified →](/about) — $299/month, cancel anytime

---

## How It Works

### Three Steps to Agent-Ready Intelligence

**Step 1: Discover**
Browse 4,039+ evaluated packages across 16 categories, or query the REST API or MCP server to find tools matching your agent's needs. Filter by category, score range, or specific capability.

**Step 2: Evaluate**
Every package is scored on five dimensions:
- **MCP Server Quality** — Does it implement the MCP spec correctly?
- **Documentation Accuracy** — Do the docs match the actual behavior?
- **Error Message Quality** — Does it return actionable errors?
- **Security Posture** — Are there known vulnerabilities or risky patterns?
- **Auth Complexity** — How hard is it to authenticate?

Scores are computed offline by automated evaluation pipelines and updated on a regular cadence.

**Step 3: Query**
At agent runtime, call the Assay API or mount the Assay MCP server. Ask "what's the best file-system tool available?" and get a ranked list with AF Scores, gotchas, and avoid-when conditions — all in a single database read. No LLM involved.

---

## FAQ

**What is the AF Score?**
AF Score stands for Agent-Friendliness Score. It's a composite rating from 0 to 100 that reflects how well a software package works in agentic contexts. It weighs MCP server quality, documentation accuracy, error message usefulness, security posture, and authentication complexity. A higher score means fewer surprises when an AI agent calls this tool.

---

**How is the AF Score calculated? Can I trust automated scores?**
Scores are computed by automated evaluation pipelines that test packages against a defined rubric — not by human opinion or vendor self-reporting. The methodology is consistent across all packages. That said, no automated system is perfect: scores reflect observable properties (spec compliance, documentation diff from behavior, error format, etc.) rather than real-world production performance. We're transparent about what we measure and how. Vendor disputes go through a documented review process.

---

**How often are scores updated?**
Scores are refreshed on a regular cadence as packages publish new versions. You can see the last-evaluated date on every package page. If you're a vendor with an API Pro or Certified subscription, you get priority re-evaluation after releases.

---

**What's the difference between the REST API and the MCP server?**
Both give access to the same ratings data. The **REST API** (`/api/v1/packages`) is a standard HTTP JSON API — useful for developers building dashboards, CI integrations, or agent orchestration systems. The **MCP server** is designed for agent-to-agent use: mount it in your agent's tool set and it can query Assay as a native tool call, selecting packages at runtime as part of its reasoning loop.

---

**What does it cost?**

| Tier | Price | What you get |
|------|-------|--------------|
| Free | $0 | Browse the full directory, read all scores, 100 API calls/day |
| Package Monitoring | $3/month per package | Score change notifications, score history, monthly mini-report, 200 API calls/day |
| Package Evaluation Report | $99 one-time | Full score breakdown, improvement recommendations, competitive positioning |
| Certified Agent-Ready | Coming later | Independent certification badge, priority re-evaluation, embeddable widget |

The directory is free forever — Assay's business model doesn't depend on paywalling the ratings.

---

**Who is Assay for? I'm not building MCP servers.**
Assay covers APIs and SDKs beyond MCP servers — any software package an agent might call. If you're building agents that integrate with third-party tools, Assay helps you select and vet those tools. If you're building tools that agents will use, Assay helps you demonstrate and improve quality.

---

**Can vendors dispute their scores?**
Yes. Vendors can submit a dispute through the Assay vendor portal, providing evidence that a score is inaccurate (e.g., a documentation accuracy score that doesn't reflect a recent update). Disputes trigger a manual review and re-evaluation. We aim to resolve disputes within 5 business days. Certified vendors get faster turnaround.

---

**Why does this exist? Didn't someone already solve this?**
Not for agent-readiness. Socket.dev solved this problem for npm security in 2022 and now processes billions of installs. The MCP ecosystem hit 17,977 servers with zero independent quality layer — the same gap, two years later. As agents become primary consumers of software interfaces, the criteria for "good" shift: error message quality, documentation accuracy, and auth complexity matter more than they did for human-facing tools. Assay is purpose-built for that evaluation.

---

**Is Assay affiliated with any package registries or vendors?**
No. Assay is an independent rating platform. Vendors can purchase the Certified Agent-Ready badge, but certification requires meeting score thresholds — it cannot be bought without earning it. Paid tiers never inflate scores. The free directory and all AF Scores are editorially independent.

---

**How do I get my package added?**
Submit a package through the vendor portal or suggest it via the API. The evaluation pipeline will pick it up in the next batch run. Certified vendors get expedited evaluation. All 242 currently evaluated packages were either submitted by vendors or added proactively based on ecosystem prevalence.

---

## Secondary CTA Section

### For Agents and Operators
Stop hardcoding tool choices. Let your agent query Assay at runtime and pick the best available tool for the job — with scores, gotchas, and avoid-when conditions included.

**[Try the API →](/api/v1/packages)**
OpenAPI spec · MCP server available · No account required for read access

---

### For Developers
4,039+ packages evaluated. 16 categories. One score per package that tells you whether it's worth integrating.

**[Browse Ratings →](/packages)**
Free · No login · Updated regularly

---

### For Vendors
Agent operators are selecting tools programmatically. Be discoverable, be scored, be certified.

**[Get Certified →](/about)**
$299/month · Cancel anytime · Badge displays on your docs and in Assay directory

---

## Footer Tagline Options

1. **Assay.** The quality layer for agentic software.
2. **Assay.** Know before your agent calls.
3. **Assay.** Ratings for the agentic era.

---

---

## "For Agents" Code Snippet Section

**Section headline**: Drop it into your agent in 30 seconds

**Subhead**: Structured JSON. Sub-millisecond reads. No LLM at query time.

### REST API Example
```bash
# Find the best payment tool for your agent
curl "https://assay.tools/v1/packages?category=payments&min_score=70&limit=5"
```

```json
{
  "packages": [
    {
      "id": "stripe-mcp",
      "name": "Stripe MCP",
      "af_score": 82,
      "security_score": 90,
      "reliability_score": 88,
      "has_mcp_server": true,
      "gotchas": ["Webhook signature validation required for all events"],
      "best_when": "Payments, subscriptions, invoicing in agent workflows"
    }
  ]
}
```

### MCP Server Example
```json
// In your agent's MCP config:
{
  "mcpServers": {
    "assay": {
      "command": "npx",
      "args": ["-y", "@assay-tools/mcp"]
    }
  }
}
```

Then your agent calls `find_packages({ category: "database", min_af_score: 70 })` or `compare_packages({ ids: ["supabase", "planetscale", "neon"] })`.

---

*Document version: 2026-03-10. Stats current as of March 2026.*
