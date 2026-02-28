You are working on the Assay project (assay.tools) — an agentic software rating platform. The codebase is at ~/git/assay/. The business docs are at ~/ai-data/projects/agentic-software-ratings/.

CONTEXT:
- MVP is built: FastAPI REST API, MCP server, Jinja2+Tailwind website, SQLite DB
- 242 packages evaluated with AF scores (average 63.7, top scorer 85.2)
- Business plan, product spec, revenue models, and hosting analysis docs exist
- Budget constraint: keep costs under $100/month for first month
- Focus verticals: developer-tools, security, database categories

YOUR TASKS FOR THIS SESSION (in priority order):

1. COST ANALYSIS — Create a detailed first-month cost breakdown at ~/ai-data/projects/agentic-software-ratings/cost-breakdown.md:
   - Hosting: Research Railway pricing for our stack (FastAPI + SQLite, MCP server)
   - Domain: assay.tools registration cost
   - Evaluation costs: We use Claude Code subscription ($200/mo already paid), so LLM eval cost is $0
   - Any other infrastructure costs
   - Total must stay under $100/mo (excluding existing Claude subscription)

2. BUSINESS PLAN ENHANCEMENT — Update ~/ai-data/projects/agentic-software-ratings/business-plan.md:
   - Add concrete pricing tiers with dollar amounts (reference revenue-and-testing.md)
   - Add comparable company revenue data (Socket.dev, Postman, etc.)
   - Add 30/60/90 day milestones
   - Add "Actions Needed from AJ" section — things only a human can do (legal entity, vendor outreach contacts, domain registration, etc.)

3. LANDING PAGE CONTENT — Create ~/git/assay/docs/landing-page-copy.md:
   - Hero headline and subheadline
   - Value proposition bullets (for agents, for developers, for vendors)
   - Social proof section (242 packages evaluated, 63 categories, etc.)
   - CTA for each audience (try the API, get certified, browse ratings)
   - FAQ section

4. WEB FRONTEND POLISH — Improve the existing website at ~/git/assay/src/assay/templates/:
   - Read the existing templates first to understand current state
   - Improve the homepage with better category browsing
   - Add search functionality if not present
   - Make the package detail page more useful (show all scores, gotchas, alternatives)
   - Ensure mobile responsiveness with Tailwind classes

5. 30-DAY LAUNCH PLAN — Create ~/ai-data/projects/agentic-software-ratings/launch-plan.md:
   - Week 1: Technical launch prep (domain, hosting, deploy)
   - Week 2: Soft launch (share in AI communities, get feedback)
   - Week 3: Vendor outreach (top 20 packages for certification)
   - Week 4: Content marketing (blog post, social, comparison guides)
   - Include specific action items tagged as [AJ] for human-required actions
   - Include specific action items tagged as [AGENT] for things Claude can do

6. BONUS: DISCOVER AND EVALUATE MORE PACKAGES — If you still have capacity after completing tasks 1-5:
   - Search GitHub for trending repos with MCP server implementations that aren't in our DB yet
   - Look beyond just "mcp" keyword — search for major APIs/SaaS tools that agents commonly use (Stripe, Twilio, GitHub, Slack, Discord, AWS, GCP, Azure, Notion, Airtable, HubSpot, Salesforce, etc.)
   - For each new package found: fetch README, write evaluation JSON to ~/git/assay/evaluations/{id}.json
   - Then load all new evaluations: cd ~/git/assay && uv run python -m assay.evaluation.loader --dir evaluations/
   - Focus on our priority verticals: developer-tools, security, database, cloud-infrastructure, communication
   - Keep going until the session ends — every additional evaluated package increases the platform's value

IMPORTANT NOTES:
- Use Sonnet-level sub-agents when you need to parallelize work
- Commit changes to git as you complete each task
- Write a session summary to ~/git/assay/logs/ when done
- Keep the "Actions for AJ" list as a prominent deliverable — he wants to see it tomorrow morning
- Be cost-conscious in all recommendations
- MAXIMIZE THIS SESSION — if you finish planned work, keep discovering and evaluating packages until time runs out
