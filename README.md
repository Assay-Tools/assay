# Assay

[![CI](https://github.com/Assay-Tools/assay/actions/workflows/ci.yml/badge.svg)](https://github.com/Assay-Tools/assay/actions/workflows/ci.yml)

**The quality layer for agentic software.**

Independent agent-friendliness ratings for MCP servers, APIs, and SDKs. Assay scores packages on documentation accuracy, error quality, security posture, and more — so agents (and developers) can pick the right tool for the job.

## What it does

- Rates 2,400+ packages on a 0-100 **AF Score** (Agent-Friendliness)
- Covers MCP servers, REST APIs, GraphQL services, and SDKs
- Scores across 5 dimensions: MCP quality, documentation, error messages, security, and auth complexity
- Provides a REST API, MCP server, and web interface

## Principles

- **Independent ratings** — vendors cannot buy influence over scores
- **Trust is the product** — if the ratings aren't honest, they're worthless
- **Built for builders** — solo developers and small shops are the core audience

## Quick start

```bash
# Clone and install
git clone https://github.com/assay-tools/assay.git
cd assay
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run locally
uvicorn assay.api.app:app --reload --port 8000
```

Visit `http://localhost:8000` for the web UI, `http://localhost:8000/docs` for API docs.

## API

```bash
# Search packages
curl 'https://assay.tools/v1/packages?q=email&limit=5'

# Get a specific package
curl 'https://assay.tools/v1/packages/resend'

# Agent-optimized guide
curl 'https://assay.tools/v1/packages/resend/agent-guide'

# Compare packages
curl 'https://assay.tools/v1/compare?ids=resend,sendgrid,postmark'

# Stats
curl 'https://assay.tools/v1/stats'
```

## MCP Server

Assay includes an MCP server so AI agents can query ratings at runtime:

```json
{
  "mcpServers": {
    "assay": {
      "command": "python",
      "args": ["-m", "assay.mcp_server"]
    }
  }
}
```

Tools: `find_packages`, `get_package`, `compare_packages`, `list_categories`

## Scoring methodology

Each package is evaluated across 5 weighted dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| MCP Quality | 20% | Tool descriptions, schema completeness, error handling |
| Documentation | 20% | Accuracy, examples, completeness for agent consumption |
| Error Messages | 15% | Actionable errors that help agents self-correct |
| Security | 15% | Auth patterns, input validation, least-privilege design |
| Auth Complexity | 15% | How easy it is for an agent to authenticate |

The AF Score is the weighted average, scaled 0-100.

## Business Model & Operations

Assay is an **agentic business** — AI agents handle evaluation, report generation, prospecting, and operational execution. See [BUSINESS.md](BUSINESS.md) for the full business model, pricing tiers, product streams, and operating philosophy.

## License

MIT
