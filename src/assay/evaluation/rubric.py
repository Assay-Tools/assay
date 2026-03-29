"""Evidence-banded scoring rubric v2 — source of truth for all 14 sub-components.

Each sub-component has ordered checkpoints. Checkpoints are cumulative:
meeting a higher checkpoint implies all lower ones are met. The score must
fall within the band of the highest met checkpoint.

Used by:
- Submission validation (score-evidence consistency checks)
- Evaluation guide generation (rendered into evaluate.md)
- Future: calibration analysis
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Checkpoint:
    """A single binary evidence checkpoint."""
    id: str               # Machine-readable ID (e.g., "has_api_docs")
    label: str            # Human-readable description
    band_min: int         # Minimum score if this is the highest met checkpoint
    band_max: int         # Maximum score if this is the highest met checkpoint


@dataclass
class SubComponentRubric:
    """Complete rubric for one sub-component."""
    id: str               # Field name (e.g., "api_doc_score")
    dimension: str        # "af", "security", or "reliability"
    name: str             # Human-readable name
    description: str      # What this measures
    checkpoints: list[Checkpoint]
    unmet_max: int = 29   # Max score when NO checkpoints are met


# ---------------------------------------------------------------------------
# Agent Friendliness (5 sub-components)
# ---------------------------------------------------------------------------

INTEGRATION_QUALITY = SubComponentRubric(
    id="integration_quality",
    dimension="af",
    name="Agent Integration Quality",
    description="Quality of the best agent integration path (MCP, REST API, SDK, CLI, etc.)",
    unmet_max=10,
    checkpoints=[
        Checkpoint("integration_exists", "A programmatic interface exists (MCP, REST, SDK, CLI, or library)", 11, 35),
        Checkpoint("integration_usable", "Interface can be installed/accessed and works reliably", 36, 55),
        Checkpoint("integration_documented", "Interface operations are documented with descriptions", 56, 74),
        Checkpoint("integration_examples", "Working usage examples or integration guide exists", 75, 89),
        Checkpoint("integration_mature", "Stable, well-designed, handles edge cases, production-ready", 90, 100),
    ],
)

API_DOC_SCORE = SubComponentRubric(
    id="api_doc_score",
    dimension="af",
    name="API Documentation Quality",
    description="Completeness and quality of API documentation",
    unmet_max=29,
    checkpoints=[
        Checkpoint("has_api_docs", "Has any API documentation", 30, 49),
        Checkpoint("has_endpoint_listings", "Docs include endpoint/function listings with parameters", 50, 64),
        Checkpoint("has_code_examples", "Docs include working code examples", 65, 79),
        Checkpoint("covers_errors", "Docs cover error responses/exceptions", 80, 89),
        Checkpoint("auto_generated", "Docs are auto-generated from source (OpenAPI, etc.) ensuring accuracy", 90, 100),
    ],
)

ERROR_HANDLING_SCORE = SubComponentRubric(
    id="error_handling_score",
    dimension="af",
    name="Error Handling Quality",
    description="How well the package communicates errors to agents",
    unmet_max=19,
    checkpoints=[
        Checkpoint("errors_exist", "Errors are returned (not silent failures)", 20, 39),
        Checkpoint("errors_structured", "Errors use structured format (JSON, typed exceptions)", 40, 59),
        Checkpoint("errors_coded", "Errors include machine-readable error codes", 60, 74),
        Checkpoint("errors_descriptive", "Error messages include actionable guidance for resolution", 75, 89),
        Checkpoint("errors_documented", "Error catalog is documented with all possible codes/scenarios", 90, 100),
    ],
)

AUTH_COMPLEXITY_SCORE = SubComponentRubric(
    id="auth_complexity_score",
    dimension="af",
    name="Auth Simplicity",
    description="How simple is authentication for an agent (100 = simplest)",
    unmet_max=19,
    checkpoints=[
        Checkpoint("auth_exists", "Authentication mechanism is documented", 20, 39),
        Checkpoint("auth_programmatic", "Auth can be done programmatically (no browser required)", 40, 59),
        Checkpoint("auth_single_step", "Auth requires a single step (e.g., one API key or token)", 60, 79),
        Checkpoint("auth_env_friendly", "Auth supports environment variables or config files", 80, 94),
        Checkpoint("auth_api_key", "Simple API key auth (generate key, set header, done)", 95, 100),
    ],
)

RATE_LIMIT_CLARITY_SCORE = SubComponentRubric(
    id="rate_limit_clarity_score",
    dimension="af",
    name="Rate Limit Clarity",
    description="How clearly rate limits are documented and communicated",
    unmet_max=19,
    checkpoints=[
        Checkpoint("rate_limits_mentioned", "Rate limits are mentioned somewhere in docs", 20, 39),
        Checkpoint("rate_limits_specific", "Specific limits are documented (e.g., 100 req/min)", 40, 59),
        Checkpoint("rate_limits_per_tier", "Limits documented per plan/tier with upgrade path", 60, 74),
        Checkpoint("rate_limits_headers", "Rate limit info returned in response headers (X-RateLimit-*)", 75, 89),
        Checkpoint("rate_limits_retry", "429 responses include Retry-After header or guidance", 90, 100),
    ],
)

# ---------------------------------------------------------------------------
# Security (5 sub-components)
# ---------------------------------------------------------------------------

TLS_ENFORCEMENT = SubComponentRubric(
    id="tls_enforcement",
    dimension="security",
    name="TLS Enforcement",
    description="Whether HTTPS/TLS is required for all communication",
    unmet_max=19,
    checkpoints=[
        Checkpoint("has_https", "Service/API is accessible over HTTPS", 20, 49),
        Checkpoint("https_default", "HTTPS is the default in docs and examples", 50, 69),
        Checkpoint("http_redirects", "HTTP requests redirect to HTTPS", 70, 84),
        Checkpoint("https_only", "HTTP is rejected or not available (HTTPS only)", 85, 94),
        Checkpoint("tls_modern", "Modern TLS (1.2+) enforced, HSTS enabled", 95, 100),
    ],
)

AUTH_STRENGTH = SubComponentRubric(
    id="auth_strength",
    dimension="security",
    name="Authentication Strength",
    description="Strength of the authentication mechanism",
    unmet_max=9,
    checkpoints=[
        Checkpoint("has_auth", "Some form of authentication is required", 10, 34),
        Checkpoint("auth_per_user", "Auth is per-user/per-account (not shared keys)", 35, 54),
        Checkpoint("auth_revocable", "Credentials can be revoked or rotated", 55, 74),
        Checkpoint("auth_scoped", "Auth supports scoped permissions (not all-or-nothing)", 75, 89),
        Checkpoint("auth_mfa_available", "MFA or additional security layers available", 90, 100),
    ],
)

SCOPE_GRANULARITY = SubComponentRubric(
    id="scope_granularity",
    dimension="security",
    name="Permission Granularity",
    description="How fine-grained are access permissions",
    unmet_max=19,
    checkpoints=[
        Checkpoint("has_permissions", "Some permission/access control model exists", 20, 39),
        Checkpoint("read_write_split", "Read and write permissions are separate", 40, 59),
        Checkpoint("resource_scoped", "Permissions can be scoped to specific resources/endpoints", 60, 79),
        Checkpoint("least_privilege", "Documentation encourages least-privilege configuration", 80, 94),
        Checkpoint("custom_roles", "Custom roles or fine-grained policy definitions supported", 95, 100),
    ],
)

DEPENDENCY_HYGIENE = SubComponentRubric(
    id="dependency_hygiene",
    dimension="security",
    name="Dependency Hygiene",
    description="Health of the dependency tree (CVEs, outdated deps)",
    unmet_max=29,
    checkpoints=[
        Checkpoint("deps_listed", "Dependencies are listed (package.json, requirements.txt, etc.)", 30, 49),
        Checkpoint("deps_pinned", "Dependencies are pinned to specific versions", 50, 64),
        Checkpoint("no_critical_cves", "No known critical CVEs in dependency tree", 65, 79),
        Checkpoint("deps_maintained", "Dependencies are actively maintained (updated within 12 months)", 80, 94),
        Checkpoint("deps_audited", "Automated dependency scanning in CI (Dependabot, Snyk, etc.)", 95, 100),
    ],
)

SECRET_HANDLING = SubComponentRubric(
    id="secret_handling",
    dimension="security",
    name="Secret Handling",
    description="How credentials and secrets are managed",
    unmet_max=19,
    checkpoints=[
        Checkpoint("no_hardcoded", "No hardcoded secrets in source code or examples", 20, 39),
        Checkpoint("env_vars_supported", "Supports environment variables for credentials", 40, 59),
        Checkpoint("secrets_not_logged", "Credentials are not included in logs or error messages", 60, 79),
        Checkpoint("vault_support", "Supports secret managers (Vault, AWS Secrets Manager, etc.)", 80, 94),
        Checkpoint("auto_rotation", "Supports automatic credential rotation", 95, 100),
    ],
)

# ---------------------------------------------------------------------------
# Reliability (4 sub-components)
# ---------------------------------------------------------------------------

UPTIME_DOCUMENTED = SubComponentRubric(
    id="uptime_documented",
    dimension="reliability",
    name="Uptime Documentation",
    description="Published SLA, status page, uptime history",
    unmet_max=19,
    checkpoints=[
        Checkpoint("uptime_mentioned", "Uptime or availability is mentioned in docs", 20, 39),
        Checkpoint("status_page", "Public status page exists", 40, 59),
        Checkpoint("sla_published", "SLA with specific uptime percentage is published", 60, 79),
        Checkpoint("incident_history", "Historical incident reports are accessible", 80, 94),
        Checkpoint("sla_backed", "SLA is contractually backed with credits/remediation", 95, 100),
    ],
)

VERSION_STABILITY = SubComponentRubric(
    id="version_stability",
    dimension="reliability",
    name="Version Stability",
    description="Stable releases, semver adherence, predictable versioning",
    unmet_max=19,
    checkpoints=[
        Checkpoint("has_releases", "Has tagged releases (not just main branch)", 20, 39),
        Checkpoint("semver", "Follows semantic versioning (or clear versioning scheme)", 40, 59),
        Checkpoint("changelog", "Changelog or release notes exist", 60, 79),
        Checkpoint("stable_release", "Has at least one stable (1.0+) release", 80, 94),
        Checkpoint("lts_available", "Long-term support or stable release channel available", 95, 100),
    ],
)

BREAKING_CHANGES_HISTORY = SubComponentRubric(
    id="breaking_changes_history",
    dimension="reliability",
    name="Breaking Changes History",
    description="Frequency and management of breaking changes (100 = rare/well-managed)",
    unmet_max=29,
    checkpoints=[
        Checkpoint("changes_documented", "Breaking changes are documented when they occur", 30, 49),
        Checkpoint("migration_guides", "Migration guides provided for breaking changes", 50, 69),
        Checkpoint("deprecation_period", "Deprecation warnings before removal (grace period)", 70, 84),
        Checkpoint("breaking_rare", "Breaking changes are rare (less than 2 per year)", 85, 94),
        Checkpoint("api_versioning", "API versioning ensures old versions continue working", 95, 100),
    ],
)

ERROR_RECOVERY = SubComponentRubric(
    id="error_recovery",
    dimension="reliability",
    name="Error Recovery",
    description="Retry guidance, idempotent operations, graceful degradation",
    unmet_max=19,
    checkpoints=[
        Checkpoint("retryable_errors", "Transient errors are distinguishable from permanent ones", 20, 39),
        Checkpoint("retry_guidance", "Retry strategy is documented (backoff, intervals)", 40, 59),
        Checkpoint("idempotent_ops", "Key operations are idempotent (safe to retry)", 60, 79),
        Checkpoint("idempotency_keys", "Idempotency keys or request IDs supported", 80, 94),
        Checkpoint("graceful_degradation", "Graceful degradation documented (fallbacks, circuit breaking)", 95, 100),
    ],
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_RUBRICS: dict[str, SubComponentRubric] = {
    r.id: r for r in [
        # AF
        INTEGRATION_QUALITY, API_DOC_SCORE, ERROR_HANDLING_SCORE,
        AUTH_COMPLEXITY_SCORE, RATE_LIMIT_CLARITY_SCORE,
        # Security
        TLS_ENFORCEMENT, AUTH_STRENGTH, SCOPE_GRANULARITY,
        DEPENDENCY_HYGIENE, SECRET_HANDLING,
        # Reliability
        UPTIME_DOCUMENTED, VERSION_STABILITY,
        BREAKING_CHANGES_HISTORY, ERROR_RECOVERY,
    ]
}

AF_RUBRICS = {k: v for k, v in ALL_RUBRICS.items() if v.dimension == "af"}
SECURITY_RUBRICS = {k: v for k, v in ALL_RUBRICS.items() if v.dimension == "security"}
RELIABILITY_RUBRICS = {k: v for k, v in ALL_RUBRICS.items() if v.dimension == "reliability"}


def validate_score_against_evidence(
    rubric: SubComponentRubric,
    score: float,
    checkpoints_met: dict[str, bool],
) -> str | None:
    """Validate that a score falls within the band implied by evidence.

    Returns an error message if inconsistent, None if valid.
    """
    # Find the highest met checkpoint
    highest_met = None
    for cp in rubric.checkpoints:
        if checkpoints_met.get(cp.id, False):
            highest_met = cp

    if highest_met is None:
        # No checkpoints met — score must be at or below unmet_max
        if score > rubric.unmet_max:
            return (
                f"{rubric.id}: score is {score} but no evidence checkpoints are met "
                f"(max allowed: {rubric.unmet_max})"
            )
        return None

    # Score must fall within the highest met checkpoint's band
    if score < highest_met.band_min or score > highest_met.band_max:
        return (
            f"{rubric.id}: score is {score} but highest evidence checkpoint "
            f"'{highest_met.id}' implies band {highest_met.band_min}-{highest_met.band_max}"
        )

    return None
