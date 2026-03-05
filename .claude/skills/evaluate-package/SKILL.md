# /evaluate-package — Assay Package Evaluation Skill

Evaluate a software package across all three Assay dimensions (Agent Friendliness, Security, Reliability) and submit the result to the Assay API.

## Usage

```
/evaluate-package <package-name-or-url>
```

Examples:
- `/evaluate-package stripe`
- `/evaluate-package https://github.com/resend/resend-node`

## What This Skill Does

1. **Discovers** the package — finds the repo URL, README, and metadata
2. **Analyzes** the package across three dimensions using the scoring rubric below
3. **Generates** structured JSON matching the Assay evaluation schema
4. **Submits** the evaluation to the Assay API via `POST /v1/evaluations`

## Scoring Rubric

### Agent Friendliness (AF) Sub-Components (each 0-100)

| Component | Weight | Scoring Guide |
|-----------|--------|---------------|
| `mcp_score` | 25% | 0=no MCP, 30=mentioned but immature, 60=functional, 80-100=mature+documented |
| `api_doc_score` | 25% | 0=none, 30=minimal, 60=adequate, 80=good, 100=excellent with examples |
| `error_handling_score` | 20% | 0=unknown/poor, 50=adequate, 80=good structured errors, 100=excellent with codes+guidance |
| `auth_complexity_score` | 15% | 100=simple API key, 70=OAuth2, 40=complex multi-step, 20=very complex |
| `rate_limit_clarity_score` | 15% | 0=not mentioned, 50=vague, 80=clear docs, 100=clear docs+headers |

### Security Sub-Components (each 0-100)

| Component | Weight | Scoring Guide |
|-----------|--------|---------------|
| `tls_enforcement` | 20% | 100=HTTPS required, 0=allows HTTP |
| `auth_strength` | 25% | 100=API keys+scopes or OAuth2, 50=basic, 0=none |
| `scope_granularity` | 20% | 100=fine-grained, 50=coarse, 0=all-or-nothing |
| `dependency_hygiene` | 15% | 100=clean deps no CVEs, 50=some issues, 0=severe |
| `secret_handling` | 20% | 100=env vars/vault never logged, 0=secrets in code/logs |

### Reliability Sub-Components (each 0-100, equal weights)

| Component | Scoring Guide |
|-----------|---------------|
| `uptime_documented` | 100=published SLA+status page, 50=mentioned, 0=none |
| `version_stability` | 100=stable semver releases, 50=some stability, 0=unstable |
| `breaking_changes_history` | 100=no breaking changes, 0=frequent breaking |
| `error_recovery` | 100=retry guidance+idempotent ops, 50=partial, 0=none |

### Score Thresholds
- 80+ = Excellent (green)
- 60-79 = Good (yellow)
- Below 60 = Needs Work (red)

## Evaluation Workflow

### Step 1: Gather Context

Use web tools to gather information:
- If a GitHub URL is provided, fetch the README and repo metadata
- If just a name, search for the package's official site and repo
- Look for: API docs, MCP server availability, authentication docs, pricing page, changelog

### Step 2: Analyze and Score

For each sub-component:
1. Find specific evidence in the gathered context
2. Score based on the rubric above
3. Note any gotchas or unusual findings

### Step 3: Build the Evaluation JSON

The evaluation JSON must match this schema:

```json
{
  "id": "package-slug",
  "name": "Package Name",
  "homepage": "https://...",
  "repo_url": "https://github.com/...",
  "category": "category-slug",
  "subcategories": [],
  "tags": ["tag1", "tag2"],
  "what_it_does": "One-line description",
  "use_cases": ["Use case 1", "Use case 2"],
  "not_for": ["Anti-pattern 1"],
  "best_when": "Best used when...",
  "avoid_when": "Avoid when...",
  "alternatives": ["alt-package-1", "alt-package-2"],
  "version_evaluated": "1.2.3",
  "interface": {
    "has_rest_api": true,
    "has_graphql": false,
    "has_grpc": false,
    "has_mcp_server": false,
    "mcp_server_url": null,
    "has_sdk": true,
    "sdk_languages": ["javascript", "python"],
    "openapi_spec_url": null,
    "webhooks": true
  },
  "auth": {
    "methods": ["api_key"],
    "oauth": false,
    "scopes": false,
    "notes": null
  },
  "pricing": {
    "model": "freemium",
    "free_tier_exists": true,
    "requires_credit_card": false,
    "notes": null
  },
  "requirements": {
    "requires_signup": true,
    "requires_credit_card": false,
    "domain_verification": false,
    "data_residency": [],
    "compliance": [],
    "min_contract": "none"
  },
  "agent_readiness": {
    "mcp_server_quality": 0,
    "documentation_accuracy": 75,
    "error_message_quality": 70,
    "error_message_notes": "Returns structured JSON errors with codes",
    "idempotency_support": "full",
    "pagination_style": "cursor",
    "retry_guidance_documented": true,
    "known_agent_gotchas": ["Rate limit resets at midnight UTC"]
  },
  "af_score_components": {
    "mcp_score": 0,
    "api_doc_score": 75,
    "error_handling_score": 70,
    "auth_complexity_score": 90,
    "rate_limit_clarity_score": 80
  },
  "security_score_components": {
    "tls_enforcement": 100,
    "auth_strength": 85,
    "scope_granularity": 60,
    "dependency_hygiene": 80,
    "secret_handling": 90,
    "security_notes": null
  },
  "reliability_score_components": {
    "uptime_documented": 90,
    "version_stability": 85,
    "breaking_changes_history": 80,
    "error_recovery": 75
  }
}
```

### Step 4: Submit

Submit the evaluation via the Assay API:

```bash
curl -X POST https://assay.tools/v1/evaluations \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $ASSAY_SUBMISSION_KEY" \
  -d @evaluation.json
```

If no API key is available, save the JSON to `evaluations/<package-id>.json` for manual loading via:
```bash
uv run python -m assay.evaluation.loader --file evaluations/<package-id>.json
```

## Category Reference

Use one of these canonical slugs for the `category` field:

| Slug | Name |
|------|------|
| `developer-tools` | Developer Tools |
| `databases` | Databases |
| `ai-ml` | AI & Machine Learning |
| `communication` | Communication |
| `file-management` | File Management |
| `cloud-infrastructure` | Cloud Infrastructure |
| `search` | Search |
| `monitoring` | Monitoring |
| `productivity` | Productivity |
| `security` | Security |
| `finance` | Finance |
| `content-management` | Content Management |
| `data-processing` | Data Processing |
| `social-media` | Social Media |
| `agent-skills` | Agent Skills |
| `other` | Other |

## Notes

- All scores are 0-100. Be honest — don't inflate.
- If you can't determine a value, use `null` rather than guessing.
- The `id` field should be a URL-safe slug (lowercase, hyphens).
- `documentation_accuracy` and `api_doc_score` measure the same thing from different angles — keep them consistent.
- `mcp_server_quality` and `mcp_score` should match.
