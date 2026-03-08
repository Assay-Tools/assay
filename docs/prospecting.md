# Assay Prospecting & Relationship Tracker

**Last Updated**: 2026-03-07

Claude manages outreach execution. AJ reviews and approves all outbound communications before sending.

See also:
- `docs/outreach-templates.md` — Message templates by scenario
- `docs/marketing.md` — Channel strategy and positioning
- `docs/utm-strategy.md` — Link tracking

---

## How This Works

1. **Claude identifies prospects** from evaluation data, community activity, or strategic fit
2. **Claude drafts outreach** using templates and context from the prospect's package evaluation
3. **AJ reviews and approves** before anything is sent
4. **Claude logs the interaction** in the tracker below
5. **Claude follows up** at appropriate intervals (with AJ's approval)

Email goes out via `hello@assay.tools` (Migadu). Claude drafts; AJ sends or approves send.

---

## Prospect Prioritization

### Tier 1: Strategic Relationships (build first)
People whose endorsement or feedback carries outsized weight.

| Priority | Why | Criteria |
|----------|-----|----------|
| Thought leaders | Credibility + amplification | Large following in AI/security space, respected opinion |
| Framework maintainers | Distribution channel | LangChain, CrewAI, AutoGen, Semantic Kernel teams |
| MCP ecosystem builders | Core audience | Smithery, Anthropic MCP team, popular MCP server authors |

### Tier 2: High-Score Package Maintainers (AF 80+)
Easiest conversation starter — "your thing is great, here's proof."

| Priority | Why | Criteria |
|----------|-----|----------|
| Active maintainers | Likely to engage, share, add badge | Recent commits, responsive to issues |
| High GitHub stars | Amplification if they share | 1K+ stars |
| Commercial products | Report upsell potential | Company behind the package |

### Tier 3: Mid-Score Package Maintainers (AF 55-75)
Improvement opportunity — genuine value exchange, report upsell.

| Priority | Why | Criteria |
|----------|-----|----------|
| Commercial APIs | $99 report = competitive intel | Company with DevRel budget |
| Growing packages | Want to improve, motivated | Rising star count, active development |

---

## Prospect Pipeline

### Active Prospects

| Name / Handle | Affiliation | Tier | Status | Last Contact | Next Action | Notes |
|---------------|-------------|------|--------|-------------|-------------|-------|
| Daniel Miessler | Fabric / UL | T1 - Thought leader | Contacted | 2026-03-07 (Discord post) | Monitor for response | Tagged in public Discord post. Idea for Assay came from his "Great Transition" video. Potential methodology advisor. |

### Identified (not yet contacted)

| Name / Handle | Affiliation | Tier | Why Target | Package/Score | Approach |
|---------------|-------------|------|------------|---------------|----------|
| Anthropic MCP team | Anthropic | T1 - Ecosystem | Their MCP servers score top-3 (93-96 AF). Natural allies. | @modelcontextprotocol/* | Congratulations template. Offer to integrate Assay scores into MCP registry. |
| Smithery.ai team | Smithery | T1 - Ecosystem | Largest MCP directory. Partnership = distribution. | N/A | Partnership pitch: Assay provides quality layer, Smithery provides discovery. |
| LangChain team | LangChain | T1 - Framework | Huge user base building agents that need tool quality signals. | N/A | Integration pitch: surface Assay scores in LangChain tool selection. |

### Completed (for reference)

| Name / Handle | Affiliation | Date | Outcome | Follow-up |
|---------------|-------------|------|---------|-----------|
| (none yet) | | | | |

---

## Relationship-Building Principles

- **Lead with value, not asks.** First contact should give them something (their score, an insight, a compliment on their work). Never lead with "can you promote us."
- **Be a person, not a brand.** AJ is the face. Messages come from AJ, not "the Assay team."
- **Respect their time.** Short messages. Clear ask (or no ask at all for first contact).
- **One touch at a time.** Don't multi-channel blast someone. Pick the right channel for the relationship.
- **Follow up exactly once.** If no response after one follow-up, move on. Don't be annoying.
- **Log everything.** Every interaction goes in the tracker so we don't double-contact or lose context.
- **Earn the right to ask.** Build genuine relationship before asking for anything (promotion, partnership, advisory role).

---

## Outreach Cadence

| Stage | Timing | Action |
|-------|--------|--------|
| Initial contact | When identified | Use appropriate template from outreach-templates.md |
| Wait for response | 5-7 business days | Do nothing. Be patient. |
| Follow-up (if no response) | Day 7-10 | One brief follow-up. Different angle or new info. |
| Move to completed | Day 14+ | If no response, log outcome as "no response" and move on. |
| Relationship maintenance | Quarterly | For active relationships: share relevant score changes, new features, ecosystem reports. |

---

## Sourcing New Prospects

Claude should proactively identify prospects during routine work:

- **During evaluations**: Flag packages with high scores + active maintainers
- **During discovery**: Note new MCP servers from known companies or individuals
- **During newsletter prep**: Identify "top movers" whose maintainers might want to know
- **During community monitoring**: Note people discussing agent tooling quality, MCP trust, etc.
- **From inbound**: Anyone who emails hello@assay.tools, submits an evaluation, or signs up for the newsletter

Add identified prospects to the "Identified" table above with context on why they're worth reaching out to.

---

## Channel Preferences by Prospect Type

| Prospect Type | Best Channel | Why |
|---------------|-------------|-----|
| OSS maintainer | GitHub issue or email | Professional, in their workflow |
| Thought leader | Twitter DM or their community | Where they're active and receptive |
| Company/DevRel | Email (hello@assay.tools) | Professional, trackable |
| Community member | Discord/forum reply | Meet them where they already are |
| Inbound contact | Reply to their channel | Match their energy and medium |
