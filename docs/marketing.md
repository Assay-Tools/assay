# Assay Marketing Playbook

**Last Updated**: 2026-03-07

Living document for marketing strategy, channel tactics, and lessons learned. See also:
- `docs/outreach-templates.md` — 1:1 outreach to package maintainers
- `docs/utm-strategy.md` — UTM parameter conventions for tracking
- `ROADMAP.md` — Strategic launch sequence

---

## Positioning

**One-liner**: Independent quality ratings for the agentic era.

**Hook**: "Which tools can your agent actually trust?"

**Elevator pitch**: Assay scores MCP servers, APIs, and SDKs across agent friendliness, security, and reliability — so agents and developers can choose the right tools. Think Consumer Reports for the AI tooling ecosystem.

**Key differentiators**:
- Independent (not a marketplace — no vendor incentives)
- Agent-first (scores what matters to autonomous agents, not just human developers)
- Evidence-based (14 sub-component rubric with checkpoints, not vibes)
- Open methodology (rubric is public, community submissions welcome)

---

## Target Audiences

### Primary: AI agent builders
- Building with MCP servers, LangChain, CrewAI, AutoGen, etc.
- Need to choose between dozens of similar tools
- Care about reliability, error handling, auth complexity
- **Where they hang out**: GitHub, Discord (Anthropic, LangChain, Fabric), Twitter/X, HN

### Secondary: DevRel / API product teams
- Want to know how their API scores against competitors
- $99 report = competitive intelligence
- Care about "agent-ready" as a positioning differentiator
- **Where they hang out**: LinkedIn, Dev.to, product communities

### Tertiary: Security-conscious developers
- Evaluating tools for production agent deployments
- Care about security scores, dependency hygiene, secret handling
- **Where they hang out**: InfoSec Twitter, Daniel Miessler's community, security Discords

---

## Channel Strategy

### Done

| Date | Channel | Action | Result |
|------|---------|--------|--------|
| 2026-03-07 | Discord (Fabric / UL) | Posted Assay link + screenshot, tagged Daniel Miessler. Follow-up: "PS: Humans can use it, too." | Pending response |

### Planned Channels (in priority order)

#### 1. Hacker News — Show HN
- **Why first**: Highest-leverage single post. Technical audience that values independent tooling.
- **Timing**: Tuesday or Wednesday, 10-11am ET. One shot — don't waste it.
- **Title**: "Show HN: Assay — Independent quality ratings for MCP servers and APIs"
- **Post body**: Keep it factual. What it does, how scoring works, link to methodology. Mention it's open for community submissions.
- **Prep before posting**:
  - [ ] Blog post published first (so HN crowd has something meaty to read)
  - [ ] Analytics deployed (need to measure the spike)
  - [ ] Site handles traffic (Railway should be fine, but verify)
- **UTM**: `?utm_source=hackernews&utm_medium=show_hn&utm_campaign=launch_2026`

#### 2. Blog post — "How We Rate 7,000 APIs for Agent-Readiness"
- **Platform**: Dev.to first (built-in distribution), cross-post to ajvanbeest.com
- **Angle**: Methodology deep-dive. Show the rubric, explain the scoring, share surprising findings.
- **Publish before HN** so the Show HN post can link to it.
- **UTM**: `?utm_source=devto&utm_medium=blog&utm_campaign=launch_2026`

#### 3. Reddit — staggered over one week
- **Subreddits** (in order):
  - r/MCP — most targeted audience, smallest community
  - r/ClaudeAI — Anthropic users building with MCP
  - r/SideProject — indie builder angle
  - r/selfhosted — if MCP server self-hosting angle resonates
  - r/programming — broadest reach, needs strong hook
- **Approach**: Different angle for each sub. Don't cross-post identical content.
- **UTM**: Per-subreddit tracking (see utm-strategy.md)

#### 4. Discord communities
- [x] Fabric / Unsupervised Learning (Daniel Miessler) — posted 2026-03-07
- [ ] Anthropic Discord — MCP channels
- [ ] LangChain Discord
- [ ] CrewAI Discord
- [ ] AI Engineer community
- **Approach**: Be a community member first. Share as "thing I built", not as marketing.

#### 5. Twitter/X
- **Angle**: Thread format. "I built a Consumer Reports for AI agent tools. Here's what 6,400 evaluations revealed."
- **Tag**: @AnthropicAI, @DanielMiessler, MCP-related accounts
- **Timing**: After HN post (ride the wave)

#### 6. Product Hunt
- **Timing**: After HN and Reddit dust settles. This is a separate launch event.
- **Prep**: Good screenshots, clear tagline, maker story.
- **UTM**: `?utm_source=producthunt&utm_medium=launch&utm_campaign=launch_2026`

#### 7. LinkedIn
- **Angle**: Professional/DevRel audience. Frame around "is your API agent-ready?"
- **Format**: Personal post from AJ, not brand post. Story of building it.
- **UTM**: `?utm_source=linkedin&utm_medium=post&utm_campaign=launch_2026`

---

## Content Ideas

### Blog posts
- "How We Rate 7,000 APIs for Agent-Readiness" (methodology deep-dive — publish first)
- "The Top 10 Most Agent-Friendly MCP Servers" (listicle — good for Reddit/HN)
- "What Makes an API Agent-Friendly? Lessons from 6,400 Evaluations" (insights piece)
- "Why Your MCP Server's Error Messages Matter More Than You Think" (specific sub-component deep-dive)

### Data-driven content
- Weekly newsletter already running (first issue sent 2026-03-07)
- Quarterly ecosystem report (template exists in `reports/templates/quarterly-ecosystem.md`)
- "Score movers" — packages whose scores changed significantly (automated via score change pipeline)

### Developer content
- "Add Assay Score Badges to Your README" (drives badge adoption = organic distribution)
- "Check Your API's Agent-Friendliness Score in CI" (GitHub Action already exists)

---

## Messaging Guidelines

- **Be honest about what we are**: An early-stage tool with real evaluations, not a polished enterprise product.
- **Lead with the problem**: "How do you know which MCP server to trust?" not "We built a rating platform."
- **Numbers are compelling**: "6,470 packages evaluated across 16 categories" is more persuasive than adjectives.
- **Acknowledge limitations**: Single-evaluator methodology, automated scoring, scores can change. Transparency builds trust.
- **Don't oversell**: "Independent ratings" not "the definitive guide." "Scores" not "certifications."
- **Humor works**: "PS: Humans can use it, too" landed well in Discord.

---

## Lessons Learned

(Update this section as we learn what works and what doesn't.)

### 2026-03-07 — First public post (Discord)
- **Channel**: Daniel Miessler's Unsupervised Learning Discord
- **What we posted**: Link + homepage screenshot + personal context ("had the idea watching Daniel's video")
- **What worked**: TBD — monitoring for responses
- **Takeaway**: TBD

---

## Metrics to Track

Once analytics are deployed:
- **Traffic by channel** (UTM-tagged)
- **Conversion funnel**: Visit → Package view → Report purchase / Email signup / Badge copy
- **API adoption**: API key registrations, MCP server connections
- **Community**: Newsletter subscribers, GitHub stars, community submissions
- **Revenue**: Brief purchases ($3), Report purchases ($99), Monitoring subs ($3/mo)
