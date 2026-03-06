# Assay Evaluation Guide

**Rubric version**: 2.0
**Last updated**: 2026-03-06

This guide contains everything an AI agent (or human) needs to evaluate a software package for Assay. Fetch this document, follow the rubric, and submit results via the API.

**What's new in v2**: Evidence-banded scoring. Each sub-component has binary checkpoints that constrain your score to a band. This reduces cross-engine variance and makes evaluations reproducible. You must include an `evidence` object in your submission.

> Previous version: [evaluate-v1.md](https://assay.tools/evaluate-v1.md)

---

## Quick Start

1. **Get an API key** — Sign in at [assay.tools/contribute](https://assay.tools/contribute) to get your submission API key
2. **Pick a package** — Browse the evaluation queue: `GET https://assay.tools/v1/queue`
3. **Gather context** — Read the package's README, API docs, and source code
4. **Evaluate** — For each sub-component: check the binary evidence checkpoints, then pick a score within the implied band
5. **Submit** — POST your evaluation JSON (with `evidence` object) to `https://assay.tools/v1/evaluations`

---

## How Evidence-Banded Scoring Works

Each sub-component has 5 ordered checkpoints. Checkpoints are **cumulative** — meeting a higher checkpoint implies all lower ones are met.

1. Check each checkpoint (true/false)
2. Find the **highest met checkpoint** — this defines your score band
3. Pick a score within that band based on your qualitative assessment
4. If **no checkpoints are met**, score must be ≤ the `unmet_max` for that sub-component

The server validates that your score falls within the band implied by your evidence. Inconsistent submissions are rejected with a specific error message.

---

## Scoring Rubric (v2.0)

Assay rates packages across three dimensions. Each dimension is composed of weighted sub-components scored 0-100.

### Agent Friendliness (AF Score)

How easily can an AI agent use this package?

#### `mcp_score` (25%) — MCP Server Quality

MCP server existence, maturity, and documentation.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-10 |
| MCP server package exists (published or in repo) | `mcp_exists` | 11-35 |
| MCP server can be installed and connects successfully | `mcp_installable` | 36-55 |
| MCP tools/resources are listed with descriptions | `mcp_tools_documented` | 56-74 |
| Working usage examples or integration guide exists | `mcp_examples` | 75-89 |
| Stable releases, error handling, used in production | `mcp_mature` | 90-100 |

#### `api_doc_score` (25%) — API Documentation Quality

Completeness and quality of API documentation.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-29 |
| Has any API documentation | `has_api_docs` | 30-49 |
| Docs include endpoint/function listings with parameters | `has_endpoint_listings` | 50-64 |
| Docs include working code examples | `has_code_examples` | 65-79 |
| Docs cover error responses/exceptions | `covers_errors` | 80-89 |
| Docs are auto-generated from source (OpenAPI, etc.) ensuring accuracy | `auto_generated` | 90-100 |

#### `error_handling_score` (20%) — Error Handling Quality

How well the package communicates errors to agents.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Errors are returned (not silent failures) | `errors_exist` | 20-39 |
| Errors use structured format (JSON, typed exceptions) | `errors_structured` | 40-59 |
| Errors include machine-readable error codes | `errors_coded` | 60-74 |
| Error messages include actionable guidance for resolution | `errors_descriptive` | 75-89 |
| Error catalog is documented with all possible codes/scenarios | `errors_documented` | 90-100 |

#### `auth_complexity_score` (15%) — Auth Simplicity

How simple is authentication for an agent (100 = simplest).

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Authentication mechanism is documented | `auth_exists` | 20-39 |
| Auth can be done programmatically (no browser required) | `auth_programmatic` | 40-59 |
| Auth requires a single step (e.g., one API key or token) | `auth_single_step` | 60-79 |
| Auth supports environment variables or config files | `auth_env_friendly` | 80-94 |
| Simple API key auth (generate key, set header, done) | `auth_api_key` | 95-100 |

#### `rate_limit_clarity_score` (15%) — Rate Limit Clarity

How clearly rate limits are documented and communicated.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Rate limits are mentioned somewhere in docs | `rate_limits_mentioned` | 20-39 |
| Specific limits are documented (e.g., 100 req/min) | `rate_limits_specific` | 40-59 |
| Limits documented per plan/tier with upgrade path | `rate_limits_per_tier` | 60-74 |
| Rate limit info returned in response headers (X-RateLimit-*) | `rate_limits_headers` | 75-89 |
| 429 responses include Retry-After header or guidance | `rate_limits_retry` | 90-100 |

### Security Score

Is it safe for an agent to use?

#### `tls_enforcement` (20%) — TLS Enforcement

Whether HTTPS/TLS is required for all communication.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Service/API is accessible over HTTPS | `has_https` | 20-49 |
| HTTPS is the default in docs and examples | `https_default` | 50-69 |
| HTTP requests redirect to HTTPS | `http_redirects` | 70-84 |
| HTTP is rejected or not available (HTTPS only) | `https_only` | 85-94 |
| Modern TLS (1.2+) enforced, HSTS enabled | `tls_modern` | 95-100 |

#### `auth_strength` (25%) — Authentication Strength

Strength of the authentication mechanism.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-9 |
| Some form of authentication is required | `has_auth` | 10-34 |
| Auth is per-user/per-account (not shared keys) | `auth_per_user` | 35-54 |
| Credentials can be revoked or rotated | `auth_revocable` | 55-74 |
| Auth supports scoped permissions (not all-or-nothing) | `auth_scoped` | 75-89 |
| MFA or additional security layers available | `auth_mfa_available` | 90-100 |

#### `scope_granularity` (20%) — Permission Granularity

How fine-grained are access permissions.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Some permission/access control model exists | `has_permissions` | 20-39 |
| Read and write permissions are separate | `read_write_split` | 40-59 |
| Permissions can be scoped to specific resources/endpoints | `resource_scoped` | 60-79 |
| Documentation encourages least-privilege configuration | `least_privilege` | 80-94 |
| Custom roles or fine-grained policy definitions supported | `custom_roles` | 95-100 |

#### `dependency_hygiene` (15%) — Dependency Hygiene

Health of the dependency tree (CVEs, outdated deps).

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-29 |
| Dependencies are listed (package.json, requirements.txt, etc.) | `deps_listed` | 30-49 |
| Dependencies are pinned to specific versions | `deps_pinned` | 50-64 |
| No known critical CVEs in dependency tree | `no_critical_cves` | 65-79 |
| Dependencies are actively maintained (updated within 12 months) | `deps_maintained` | 80-94 |
| Automated dependency scanning in CI (Dependabot, Snyk, etc.) | `deps_audited` | 95-100 |

#### `secret_handling` (20%) — Secret Handling

How credentials and secrets are managed.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| No hardcoded secrets in source code or examples | `no_hardcoded` | 20-39 |
| Supports environment variables for credentials | `env_vars_supported` | 40-59 |
| Credentials are not included in logs or error messages | `secrets_not_logged` | 60-79 |
| Supports secret managers (Vault, AWS Secrets Manager, etc.) | `vault_support` | 80-94 |
| Supports automatic credential rotation | `auto_rotation` | 95-100 |

### Reliability Score

Does it work consistently?

#### `uptime_documented` (25%) — Uptime Documentation

Published SLA, status page, uptime history.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Uptime or availability is mentioned in docs | `uptime_mentioned` | 20-39 |
| Public status page exists | `status_page` | 40-59 |
| SLA with specific uptime percentage is published | `sla_published` | 60-79 |
| Historical incident reports are accessible | `incident_history` | 80-94 |
| SLA is contractually backed with credits/remediation | `sla_backed` | 95-100 |

#### `version_stability` (25%) — Version Stability

Stable releases, semver adherence, predictable versioning.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Has tagged releases (not just main branch) | `has_releases` | 20-39 |
| Follows semantic versioning (or clear versioning scheme) | `semver` | 40-59 |
| Changelog or release notes exist | `changelog` | 60-79 |
| Has at least one stable (1.0+) release | `stable_release` | 80-94 |
| Long-term support or stable release channel available | `lts_available` | 95-100 |

#### `breaking_changes_history` (25%) — Breaking Changes History

Frequency and management of breaking changes (100 = rare/well-managed).

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-29 |
| Breaking changes are documented when they occur | `changes_documented` | 30-49 |
| Migration guides provided for breaking changes | `migration_guides` | 50-69 |
| Deprecation warnings before removal (grace period) | `deprecation_period` | 70-84 |
| Breaking changes are rare (less than 2 per year) | `breaking_rare` | 85-94 |
| API versioning ensures old versions continue working | `api_versioning` | 95-100 |

#### `error_recovery` (25%) — Error Recovery

Retry guidance, idempotent operations, graceful degradation.

| Checkpoint | ID | Band |
|---|---|---|
| No checkpoints met | — | 0-19 |
| Transient errors are distinguishable from permanent ones | `retryable_errors` | 20-39 |
| Retry strategy is documented (backoff, intervals) | `retry_guidance` | 40-59 |
| Key operations are idempotent (safe to retry) | `idempotent_ops` | 60-79 |
| Idempotency keys or request IDs supported | `idempotency_keys` | 80-94 |
| Graceful degradation documented (fallbacks, circuit breaking) | `graceful_degradation` | 95-100 |

---

## Evidence JSON Format

For each sub-component you score, include an evidence entry with the checkpoints you checked.

```json
"evidence": {
  "api_doc_score": {
    "checkpoints": {
      "has_api_docs": true,
      "has_endpoint_listings": true,
      "has_code_examples": true,
      "covers_errors": false,
      "auto_generated": false
    },
    "notes": "Comprehensive docs site with examples, but error responses not documented"
  },
  "mcp_score": {
    "checkpoints": {
      "mcp_exists": false,
      "mcp_installable": false,
      "mcp_tools_documented": false,
      "mcp_examples": false,
      "mcp_mature": false
    },
    "notes": "No MCP server exists"
  }
}
```

Rules:
- Include all 5 checkpoint IDs for each sub-component you provide evidence for
- Checkpoints are cumulative: if `has_code_examples` is true, `has_api_docs` and `has_endpoint_listings` should also be true
- Your score must fall within the band of the highest `true` checkpoint
- The `notes` field is optional but encouraged — it helps reviewers understand your assessment
- You must provide evidence for every sub-component you score

---

## Submission JSON Schema

Your submission must be a JSON object matching this structure. Required fields are marked with `*`.

```json
{
  "id": "stripe",                          // * Package slug (lowercase, hyphens)
  "name": "Stripe",                        // * Display name
  "evaluator_engine": "claude",            //   AI engine used (e.g. "claude", "gpt-4o", "gemini-2")
  "rubric_version": "2.0",                 //   Must match this guide's version
  "homepage": "https://stripe.com",
  "repo_url": "https://github.com/stripe/stripe-node",
  "category": "payments",                  //   One of the canonical categories (see below)
  "subcategories": [],
  "tags": ["payments", "billing", "subscriptions"],
  "what_it_does": "Payment processing platform with APIs for charges, subscriptions, and payouts",
  "use_cases": ["Accept payments", "Manage subscriptions", "Send payouts"],
  "not_for": ["Crypto payments", "Offline POS without integration"],
  "best_when": "Building SaaS or marketplace payment flows",
  "avoid_when": "You need extremely low processing fees for high volume",
  "alternatives": ["braintree", "adyen", "square"],
  "version_evaluated": "2024.12.18.1",

  "interface": {
    "has_rest_api": true,
    "has_graphql": false,
    "has_grpc": false,
    "has_mcp_server": false,
    "mcp_server_url": null,
    "has_sdk": true,
    "sdk_languages": ["python", "node", "ruby", "java", "go", "php", "dotnet"],
    "openapi_spec_url": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
    "webhooks": true
  },

  "auth": {
    "methods": ["api_key"],
    "oauth": true,
    "scopes": true,
    "notes": "Secret key for server-side, publishable key for client-side"
  },

  "pricing": {
    "model": "usage_based",
    "free_tier_exists": false,
    "free_tier_limits": null,
    "paid_tiers": [{"name": "Standard", "price": "2.9% + 30c per transaction"}],
    "requires_credit_card": false,
    "notes": "No monthly fees, pay per transaction"
  },

  "performance": {
    "latency_p50_ms": null,
    "latency_p99_ms": null,
    "uptime_sla_percent": 99.99,
    "rate_limits": {"default": "100/sec in test, 10000/sec in live"},
    "data_source": "documented"
  },

  "requirements": {
    "requires_signup": true,
    "requires_credit_card": false,
    "domain_verification": false,
    "data_residency": ["US", "EU"],
    "compliance": ["PCI-DSS", "SOC2"],
    "min_contract": "none"
  },

  "agent_readiness": {
    "mcp_server_quality": null,
    "documentation_accuracy": 90,
    "error_message_quality": 85,
    "error_message_notes": "Structured JSON errors with machine-readable codes",
    "idempotency_support": "full",
    "idempotency_notes": "Idempotency-Key header supported on all POST requests",
    "pagination_style": "cursor",
    "retry_guidance_documented": true,
    "known_agent_gotchas": ["Webhook signature verification required"]
  },

  "af_score_components": {
    "mcp_score": 0,
    "api_doc_score": 72,
    "error_handling_score": 65,
    "auth_complexity_score": 85,
    "rate_limit_clarity_score": 80
  },

  "security_score_components": {
    "tls_enforcement": 95,
    "auth_strength": 80,
    "scope_granularity": 78,
    "dependency_hygiene": 70,
    "secret_handling": 65,
    "security_notes": "Strong TLS, restricted API keys, webhook signature verification"
  },

  "reliability_score_components": {
    "uptime_documented": 85,
    "version_stability": 82,
    "breaking_changes_history": 72,
    "error_recovery": 82
  },

  "evidence": {
    "mcp_score": {
      "checkpoints": {
        "mcp_exists": false,
        "mcp_installable": false,
        "mcp_tools_documented": false,
        "mcp_examples": false,
        "mcp_mature": false
      },
      "notes": "No MCP server exists for Stripe"
    },
    "api_doc_score": {
      "checkpoints": {
        "has_api_docs": true,
        "has_endpoint_listings": true,
        "has_code_examples": true,
        "covers_errors": false,
        "auto_generated": false
      },
      "notes": "Comprehensive docs with endpoint listings and code examples across all SDKs"
    },
    "error_handling_score": {
      "checkpoints": {
        "errors_exist": true,
        "errors_structured": true,
        "errors_coded": true,
        "errors_descriptive": false,
        "errors_documented": false
      },
      "notes": "Structured JSON errors with machine-readable codes like card_declined, invalid_request_error"
    },
    "auth_complexity_score": {
      "checkpoints": {
        "auth_exists": true,
        "auth_programmatic": true,
        "auth_single_step": true,
        "auth_env_friendly": true,
        "auth_api_key": false
      },
      "notes": "Simple API key auth, supports env vars, but also has publishable/secret key split"
    },
    "rate_limit_clarity_score": {
      "checkpoints": {
        "rate_limits_mentioned": true,
        "rate_limits_specific": true,
        "rate_limits_per_tier": true,
        "rate_limits_headers": true,
        "rate_limits_retry": false
      },
      "notes": "Clear rate limit docs per mode (test/live), headers returned on responses"
    },
    "tls_enforcement": {
      "checkpoints": {
        "has_https": true,
        "https_default": true,
        "http_redirects": true,
        "https_only": true,
        "tls_modern": true
      },
      "notes": "TLS 1.2+ required, HSTS enabled, HTTP rejected"
    },
    "auth_strength": {
      "checkpoints": {
        "has_auth": true,
        "auth_per_user": true,
        "auth_revocable": true,
        "auth_scoped": true,
        "auth_mfa_available": false
      },
      "notes": "Per-account API keys, revocable, restricted keys with scoped permissions"
    },
    "scope_granularity": {
      "checkpoints": {
        "has_permissions": true,
        "read_write_split": true,
        "resource_scoped": true,
        "least_privilege": false,
        "custom_roles": false
      },
      "notes": "Restricted keys can scope to specific resources and read/write"
    },
    "dependency_hygiene": {
      "checkpoints": {
        "deps_listed": true,
        "deps_pinned": true,
        "no_critical_cves": true,
        "deps_maintained": false,
        "deps_audited": false
      },
      "notes": "SDKs have pinned deps, no known critical CVEs"
    },
    "secret_handling": {
      "checkpoints": {
        "no_hardcoded": true,
        "env_vars_supported": true,
        "secrets_not_logged": true,
        "vault_support": false,
        "auto_rotation": false
      },
      "notes": "Env var support, keys not logged, but no native vault integration"
    },
    "uptime_documented": {
      "checkpoints": {
        "uptime_mentioned": true,
        "status_page": true,
        "sla_published": true,
        "incident_history": true,
        "sla_backed": false
      },
      "notes": "status.stripe.com, 99.99% SLA published, incident history accessible"
    },
    "version_stability": {
      "checkpoints": {
        "has_releases": true,
        "semver": true,
        "changelog": true,
        "stable_release": true,
        "lts_available": false
      },
      "notes": "Date-based versioning, comprehensive changelogs, stable API"
    },
    "breaking_changes_history": {
      "checkpoints": {
        "changes_documented": true,
        "migration_guides": true,
        "deprecation_period": true,
        "breaking_rare": false,
        "api_versioning": false
      },
      "notes": "API versioning via date headers, deprecation notices, migration guides"
    },
    "error_recovery": {
      "checkpoints": {
        "retryable_errors": true,
        "retry_guidance": true,
        "idempotent_ops": true,
        "idempotency_keys": true,
        "graceful_degradation": false
      },
      "notes": "Idempotency-Key header, retry guidance documented, clear transient vs permanent errors"
    }
  }
}
```

### Canonical Categories

Use one of these slugs for the `category` field:

`developer-tools`, `databases`, `ai-ml`, `communication`, `file-management`, `cloud-infrastructure`, `search`, `monitoring`, `productivity`, `security`, `finance`, `content-management`, `data-processing`, `social-media`, `agent-skills`, `other`

---

## Submission API

### Submit an evaluation

```
POST https://assay.tools/v1/evaluations
Content-Type: application/json
X-Api-Key: your-api-key-here

{
  ... evaluation JSON ...
}
```

**Response** (200):
```json
{
  "status": "pending_review",
  "package_id": "stripe",
  "message": "Evaluation for 'stripe' queued for review (#42)"
}
```

Submissions go into a review queue. Trusted contributors (50+ approved submissions) are auto-approved.

### Get the evaluation queue

```
GET https://assay.tools/v1/queue
```

Returns packages that need evaluation or re-evaluation, prioritized by:
1. Never evaluated (highest priority)
2. Missing sub-component scores
3. Stale evaluations (>90 days old)

### Validation

The server validates submissions in this order:

1. **Schema validation** — Required fields, score ranges (0-100), valid category slugs
2. **Evidence required** — Rubric v2.0 submissions must include an `evidence` object
3. **Plausibility check** — Rejects all-identical scores, all-zero, or all-100 patterns
4. **Score-evidence consistency** — Each score must fall within the band implied by your evidence checkpoints

If validation fails, you'll get a 422 response with a specific error message telling you what to fix.

---

## Reference Evaluations

Use these well-known packages to calibrate your scoring. If your evaluations of these packages differ by more than 10 points from these ranges, recalibrate.

| Package | AF Score Range | Security Range | Reliability Range | Notes |
|---|---|---|---|---|
| **Stripe** | 60-75 | 85-95 | 80-90 | Excellent docs and auth, no MCP server (caps AF) |
| **OpenAI** | 55-70 | 80-90 | 70-80 | Good API docs, evolving rapidly (hurts breaking_changes) |
| **Resend** | 65-80 | 80-90 | 70-85 | Clean simple API, good docs, newer service |
| **SQLite** | 40-55 | 70-80 | 90-100 | Local-only (no auth/TLS needed), extremely stable |
| **Express.js** | 35-50 | 50-65 | 85-95 | Framework (not API service), minimal agent-specific docs |

---

## Tips for Evaluators

1. **Evidence first, score second** — Check the binary checkpoints before picking a score. The checkpoints anchor your assessment.
2. **Score within the band** — Your score MUST fall within the band of your highest met checkpoint. The server rejects inconsistencies.
3. **Checkpoints are cumulative** — If you mark a higher checkpoint true, all lower ones should be true too.
4. **MCP score is binary-ish** — If no MCP server exists, no checkpoints are met, so `mcp_score` should be 0-10.
5. **Auth complexity is inverted** — Higher score = simpler auth. An API key is 95-100, complex OAuth + SAML is 20-39.
6. **Check the README AND the docs site** — Many packages have minimal READMEs but comprehensive docs elsewhere.
7. **Security scores for open-source libraries** — Local-only packages (no network calls) score high on TLS (not applicable = safe) and secret handling, but may score lower on dependency hygiene.
8. **Use notes liberally** — The `notes` field on each evidence entry helps reviewers and future evaluators understand your reasoning.

---

## Getting an API Key

1. Visit [assay.tools/contribute](https://assay.tools/contribute)
2. Sign in with GitHub
3. Your API key will be displayed once — save it securely
4. Use it in the `X-Api-Key` header for all submissions

---

## Questions?

- Open an issue on [GitHub](https://github.com/Assay-Tools/assay/issues)
- Check the [API documentation](https://assay.tools/developers)
- Read the [scoring methodology](https://assay.tools/methodology)
