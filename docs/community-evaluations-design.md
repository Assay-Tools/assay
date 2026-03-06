# Community Evaluation Submission System — Design Document

**Status**: Design complete, pending implementation
**Author**: AJ + Claude
**Date**: 2026-03-06
**Rubric version**: This document defines the path from v1 (current) to v2 (evidence-banded)

---

## Problem Statement

Assay currently has 2,456+ evaluations, all produced by Claude via an internal evaluation agent (`src/assay/evaluation/evaluator.py`). This creates two limitations:

1. **Single-engine bias** — All scores reflect Claude's interpretation of "good documentation" or "strong auth." Other engines may score differently.
2. **Scaling bottleneck** — Only AJ can trigger evaluations. Community contributions would expand coverage and add cross-engine validation.

Opening submissions to community evaluators (humans or AI agents) requires solving:
- **Cross-engine scoring consistency** — Different AI engines interpreting the same rubric produce 10-20 point variance on sub-components.
- **Submission security** — Preventing spam, gaming, and low-quality submissions without manual review of every submission.

---

## 1. Evidence-Banded Scoring Rubric

### Concept

Keep the 0-100 continuous scale but add 3-5 binary evidence checkpoints per sub-component that define score bands. The evaluating agent must report which checkpoints are met, and the score must fall within the implied band.

This constrains interpretation to ~15 points per band. When aggregated across sub-components with their weights (0.15-0.25), aggregate variance drops to ~5 points.

### Example: `api_doc_score`

| Checkpoint | Met? | Band |
|---|---|---|
| Has any API documentation | No → score must be 0-29 | 0-29 |
| Docs include endpoint/function listings with params | Yes minimum → 30-49 | 30-49 |
| Docs include working code examples | Yes minimum → 50-69 | 50-69 |
| Docs cover error responses/exceptions | Yes minimum → 70-84 | 70-84 |
| Docs are auto-generated from source (OpenAPI, etc.) ensuring accuracy | Yes → eligible for 85-100 | 85-100 |

Checkpoints are cumulative — higher checkpoints imply all lower ones are met. The agent picks a score within the band of their highest met checkpoint.

### All 14 Sub-Components

Evidence checkpoints for each sub-component will be designed in a dedicated Phase 3 session. The full list of sub-components needing checkpoints:

**Agent Friendliness (5)** — weights from `evaluator.py:AF_WEIGHTS`:
| Sub-component | Weight | What it measures |
|---|---|---|
| `mcp_score` | 0.25 | MCP server existence + quality |
| `api_doc_score` | 0.25 | API documentation quality |
| `error_handling_score` | 0.20 | Error communication quality |
| `auth_complexity_score` | 0.15 | Authentication simplicity (100=simple API key) |
| `rate_limit_clarity_score` | 0.15 | Rate limit documentation clarity |

**Security (5)** — weights from `evaluator.py:SECURITY_WEIGHTS`:
| Sub-component | Weight | What it measures |
|---|---|---|
| `tls_enforcement` | 0.20 | TLS/HTTPS requirement |
| `auth_strength` | 0.25 | Auth mechanism strength |
| `scope_granularity` | 0.20 | Permission granularity |
| `dependency_hygiene` | 0.15 | Dependency health (CVEs, outdated deps) |
| `secret_handling` | 0.20 | Secret/credential management |

**Reliability (4)** — weights from `evaluator.py:RELIABILITY_WEIGHTS`:
| Sub-component | Weight | What it measures |
|---|---|---|
| `uptime_documented` | 0.25 | SLA/uptime documentation |
| `version_stability` | 0.25 | Stable releases, semver adherence |
| `breaking_changes_history` | 0.25 | Breaking change frequency (100=none) |
| `error_recovery` | 0.25 | Retry guidance, graceful degradation |

### Handling Existing Evaluations

- Tag all existing evaluations: `rubric_version: "1.0"`, `evaluator_engine: "claude"`
- Do NOT invalidate existing scores
- They age out naturally via the existing 90-day staleness mechanism
- New v2 rubric evaluations gradually replace them
- During transition, server accepts both v1 (no evidence required) and v2 (evidence required) submissions

### Evidence JSON Format

Submissions under rubric v2 include an `evidence` object alongside scores:

```json
{
  "rubric_version": "2.0",
  "evaluator_engine": "gemini",
  "af_score_components": {
    "mcp_score": 65,
    "api_doc_score": 72,
    "error_handling_score": 55,
    "auth_complexity_score": 85,
    "rate_limit_clarity_score": 40
  },
  "evidence": {
    "api_doc_score": {
      "checkpoints": {
        "has_api_docs": true,
        "has_endpoint_listings_with_params": true,
        "has_working_code_examples": true,
        "covers_error_responses": true,
        "auto_generated_from_source": false
      },
      "highest_band": "70-84",
      "notes": "Comprehensive docs with examples, but manually maintained"
    }
  }
}
```

---

## 2. Authentication: GitHub OAuth

### Why GitHub OAuth

| Alternative | Problem |
|---|---|
| Env-var API keys (current) | Manual issuance, no identity, doesn't scale |
| Self-service API keys (no identity) | No trust signal, easy to spam |
| GitHub OAuth | Free, self-service, identity verification via account age/repos/activity |

### Registration Flow

1. Register GitHub OAuth App at `github.com/settings/developers`
   - Callback URL: `https://assay.tools/auth/callback`
   - Homepage URL: `https://assay.tools`
2. Contributor visits `/contribute` → clicks "Sign in with GitHub"
3. GitHub redirects to `/auth/callback` with authorization code
4. Server exchanges code for access token, fetches GitHub profile
5. Create/update `Contributor` record
6. Issue Assay API key (random 32-byte hex, stored as SHA-256 hash)
7. Return API key to contributor (shown once, never again)
8. Contributor uses `X-Api-Key: <key>` header for all submissions

### What We Store

- GitHub user ID (integer, stable across username changes)
- GitHub username (for display)
- Avatar URL (for contributor profiles)
- Account creation date (trust signal)
- We do NOT store the GitHub OAuth access token — use it once to get profile, then discard

### New Database Model: `Contributor`

```python
class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    github_username: Mapped[str] = mapped_column(String(255), nullable=False)
    github_avatar_url: Mapped[str | None] = mapped_column(String(512))
    github_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email: Mapped[str | None] = mapped_column(String(255))
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # SHA-256

    trust_tier: Mapped[str] = mapped_column(String(20), default="new")  # new/established/trusted
    submissions_count: Mapped[int] = mapped_column(Integer, default=0)
    approved_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=...)
    last_submission_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### Migration from Env-Var Keys

Phase 2 replaces `SUBMISSION_API_KEYS` / `ADMIN_API_KEYS` env vars (currently used in `submission_routes.py:_parse_keys()`) with DB-backed contributor keys. Admin functionality remains separate — AJ's account gets `trusted` tier + admin flag.

### New Files

- `src/assay/auth/__init__.py` — OAuth flow module
- `src/assay/auth/github.py` — GitHub OAuth client (exchange code, fetch profile)
- `src/assay/auth/middleware.py` — API key lookup, contributor resolution

---

## 3. Trust Tiers

| Tier | How to reach | Submission rate | Review policy |
|---|---|---|---|
| `new` | Just registered | 5/day | All go to pending review queue |
| `established` | 10+ approved, <20% rejection rate | 20/day | Still reviewed, but prioritized |
| `trusted` | 50+ approved, <10% rejection, manually promoted by admin | 50/day | Auto-approved (bypass queue) |

### Tier Promotion

- `new` → `established`: Automatic when thresholds met (checked on each submission)
- `established` → `trusted`: Requires manual promotion by admin via `/admin` endpoint
- Demotion: If rejection rate exceeds tier threshold, demote on next submission

### Rate Limiting

Per-contributor rate limits replace the current per-IP rate limit (`submission_routes.py:SUBMISSION_RATE_LIMIT = "20/day"`). Keyed by `contributor.id` rather than IP.

---

## 4. Submission Validation (Layered)

Validation layers execute in order. Each layer can reject or flag a submission.

### Layer 1: Schema Validation (existing)

Pydantic models in `schemas.py` already enforce:
- 0-100 ranges on all score fields (`Field(ge=0, le=100)`)
- Required fields, valid types
- Category slugs (validated against canonical list in loader)

### Layer 2: Plausibility Checks (new)

```
REJECT if all 14 sub-component scores are identical (bot/spam signal)
REJECT if any component is 0 while others are >80 without explanation in evidence
REJECT if aggregate score is exactly 0 or exactly 100 (almost never legitimate)
```

### Layer 3: Evidence Consistency (rubric v2 only)

Server checks that reported scores fall within the band implied by evidence checkpoints:

```
For each sub-component with evidence:
  - Determine highest met checkpoint → implied band
  - If score falls outside band → REJECT with specific error:
    "api_doc_score is 90 but evidence shows highest checkpoint is
     'covers_error_responses' (band 70-84)"
```

This is the key mechanism that constrains cross-engine variance.

### Layer 4: Outlier Detection

```
If package already has 2+ evaluations:
  - Compute mean aggregate score across existing evaluations
  - If new submission differs by >25 points on any aggregate dimension → FLAG for manual review
  - Flagged regardless of trust tier
```

### Layer 5: Anti-Gaming

```
Max 2 submissions per package per contributor per 30 days
Cross-reference contributor GitHub org/email against package homepage domain:
  - If match → FLAG as potential self-evaluation
  - Require explicit disclosure field in submission
  - Self-evaluations are not rejected, just flagged and disclosed on display
```

---

## 5. The Portable Evaluation Guide

A single markdown document served at `https://assay.tools/evaluate.md`.

### Purpose

Any AI agent (Claude, GPT, Gemini, Llama, etc.) can fetch this URL, read the rubric, gather package context, evaluate, and submit results — no Assay-specific tooling required.

### Contents

1. **Rubric version** — `rubric_version: 2.0` at top
2. **Quick start** — Fetch evaluation queue → gather package context → evaluate → submit
3. **Full JSON schema** — Inline, generated from Pydantic models in `schemas.py`
4. **Evidence-banded rubric** — All 14 sub-components with checkpoint definitions
5. **Evidence JSON format** — How to report which checkpoints were met
6. **Complete `curl` example** — Full submission request
7. **Reference evaluations** — 3-5 well-known packages (e.g., Stripe, Twilio, OpenAI) with expected score ranges for self-calibration
8. **API key acquisition** — Link to GitHub OAuth flow on `/contribute`
9. **Evaluation queue API** — `GET /v1/packages?status=discovered&limit=10` for packages needing evaluation

### Versioning

- URL `https://assay.tools/evaluate.md` always serves the latest version
- Previous versions at `/evaluate-v1.md`, `/evaluate-v2.md`, etc.
- Submissions must include `rubric_version` field
- Server accepts all known versions during transition periods

### Linking

The guide is linked from:
- `/contribute` page — prominent "Agent Evaluation Guide" button
- `/developers` page — in the API documentation section
- `llms-full.txt` (if created) — for LLM discoverability
- Repository README — in the contributing section

### Implementation

Served as a static file from `src/assay/static/evaluate.md`. Route added in `web_routes.py`:

```python
@router.get("/evaluate.md")
async def evaluation_guide():
    return FileResponse("src/assay/static/evaluate.md", media_type="text/markdown")
```

---

## 6. Confidence Display (Future — Phase 4)

When packages accumulate multiple independent evaluations, display a confidence indicator:

| Evaluations | Condition | Label |
|---|---|---|
| 1 | — | "Single evaluation" |
| 2+ | Same engine, within 10 points | "Consistent" |
| 2+ | Different engines, within 10 points | "Cross-validated" |
| 3+ | Different engines, within 10 points | "High confidence" |

This is a computed property derived from `EvaluationRun` records — not stored in the database. Displayed on package detail pages next to the score.

---

## 7. Implementation Roadmap

### Phase 1: Foundation (1 session)

**Goal**: Make the current system externally usable without changing auth.

- [ ] Create the evaluation guide markdown (`src/assay/static/evaluate.md`) with current v1 rubric, JSON schema, curl examples
- [ ] Add `evaluator_engine` and `rubric_version` fields to `EvaluationSubmission` schema in `schemas.py`
- [ ] Add `evaluator_engine` column to `EvaluationRun` model in `package.py`
- [ ] DB migration for new column
- [ ] Serve guide at `/evaluate.md` (route in `web_routes.py`)
- [ ] Update `/contribute` page template to link to the guide

### Phase 2: GitHub OAuth + Contributor Model (1-2 sessions)

**Goal**: Replace env-var API keys with self-service contributor identity.

- [ ] Register GitHub OAuth App (manual step — github.com/settings/developers)
- [ ] Create `Contributor` model and DB migration
- [ ] Implement OAuth flow: `/auth/github` (redirect), `/auth/callback` (exchange + create contributor)
- [ ] Implement API key issuance (random bytes → SHA-256 hash stored)
- [ ] Migrate `submission_routes.py` from `_parse_keys()` to DB-backed key lookup
- [ ] Add per-contributor rate limiting based on trust tier
- [ ] Add plausibility validation (Layer 2) to submission endpoint
- [ ] Create `/contribute` page with "Sign in with GitHub" button

### Phase 3: Evidence-Banded Rubric v2 (1 dedicated session)

**Goal**: Constrain cross-engine scoring variance to ~5 points.

- [ ] Design evidence checkpoints for all 14 sub-components (most labor-intensive step)
- [ ] Create rubric v2 evaluation guide (`src/assay/static/evaluate.md` update)
- [ ] Add `evidence` field to submission schema
- [ ] Add evidence JSON validation to submission endpoint (Layer 3)
- [ ] Add score-evidence consistency checks
- [ ] Tag existing evaluations as `rubric_version: "1.0"`, `evaluator_engine: "claude"`
- [ ] Archive v1 guide to `/evaluate-v1.md`

### Phase 4: Calibration + Confidence (ongoing)

**Goal**: Build trust in multi-engine evaluation accuracy.

- [ ] Bias analysis script — compare per-engine scoring tendencies on overlapping packages
- [ ] Confidence indicator on package detail pages
- [ ] Self-evaluation detection (GitHub org/domain matching)
- [ ] Calibration offsets if systematic bias detected (e.g., "GPT averages +8 on security")
- [ ] Admin dashboard for reviewing flagged submissions with score diffs
- [ ] Contributor profile pages showing submission history and accuracy

---

## 8. Key Files Reference

| File | Role | Phase |
|---|---|---|
| `src/assay/api/submission_routes.py` | Submission endpoint — extend with validation, contributor tracking | 1-3 |
| `src/assay/api/schemas.py` | Pydantic models — add evaluator_engine, rubric_version, evidence | 1, 3 |
| `src/assay/models/package.py` | DB models — add Contributor, extend EvaluationRun | 1, 2 |
| `src/assay/evaluation/evaluator.py` | Current rubric/system prompt — source of truth for guide | 1 |
| `src/assay/templates/pages/contribute.html` | Update to link to evaluation guide, add OAuth button | 1, 2 |
| `src/assay/templates/pages/developers.html` | Add submission workflow docs | 1 |
| `src/assay/api/web_routes.py` | Add route for `/evaluate.md` and OAuth endpoints | 1, 2 |
| **New**: `src/assay/static/evaluate.md` | The portable evaluation guide | 1, 3 |
| **New**: `src/assay/auth/__init__.py` | GitHub OAuth flow module | 2 |
| **New**: `src/assay/auth/github.py` | GitHub OAuth client | 2 |
| **New**: `src/assay/auth/middleware.py` | API key lookup, contributor resolution | 2 |
| **New**: `docs/community-evaluations-design.md` | This design document | — |

---

## 9. Open Questions

1. **Evaluation queue priority**: Should community evaluators see a prioritized queue (popular packages first, stale packages first), or just the raw list? Leaning toward staleness-first to maximize freshness.
2. **Contributor attribution**: Display contributor GitHub username on package detail pages? Pro: recognition and accountability. Con: potential gaming for visibility. Leaning toward yes with a "contributors" section.
3. **Re-evaluation triggers**: Should a new version of a package automatically move it to "needs re-evaluation" status? The 90-day staleness mechanism handles this loosely, but version-aware triggers would be more precise.
4. **Engine-specific calibration**: If systematic bias is detected (e.g., GPT always scores security 8 points higher), apply offsets automatically or just flag for human review? Leaning toward flagging first, offsets only after statistical confidence.
