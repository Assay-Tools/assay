"""Pydantic response models for the Assay API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# --- Health ---

class HealthResponse(BaseModel):
    status: str = Field("ok", description="API status")
    version: str = Field("0.1.0", description="API version")


# --- Packages ---

class PackageListResponse(BaseModel):
    packages: list[dict] = Field(
        default_factory=list, description="List of package objects",
    )
    total: int = Field(description="Total matching packages (before pagination)")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Offset into results")


# --- Categories ---

class CategoryItem(BaseModel):
    slug: str = Field(description="URL-safe category identifier")
    name: str = Field(description="Display name")
    description: str | None = Field(None, description="Category description")
    package_count: int = Field(0, description="Number of evaluated packages")


class CategoryListResponse(BaseModel):
    categories: list[CategoryItem] = Field(
        default_factory=list, description="All categories",
    )


class CategoryPackagesResponse(BaseModel):
    category: CategoryItem = Field(description="Category metadata")
    packages: list[dict] = Field(
        default_factory=list, description="Packages in this category",
    )


# --- Compare ---

class CompareResponse(BaseModel):
    packages: list[dict] = Field(
        default_factory=list, description="Packages to compare",
    )


# --- Stats ---

class ScoreDistribution(BaseModel):
    excellent: int = Field(description="Packages with AF score >= 80")
    good: int = Field(description="Packages with AF score 60-79")
    fair: int = Field(description="Packages with AF score 40-59")
    poor: int = Field(description="Packages with AF score < 40")
    unrated: int = Field(description="Packages without an AF score")


class StatsResponse(BaseModel):
    total_packages: int = Field(description="Total packages in database")
    total_evaluated: int = Field(0, description="Packages with AF scores")
    total_categories: int = Field(description="Number of categories")
    avg_af_score: float | None = Field(
        description="Average AF score across evaluated packages",
    )
    score_distribution: ScoreDistribution = Field(
        description="Breakdown by score tier",
    )


# --- Evaluation Submission ---

class EvaluationInterfaceSubmission(BaseModel):
    has_rest_api: bool = False
    has_graphql: bool = False
    has_grpc: bool = False
    has_mcp_server: bool = False
    mcp_server_url: str | None = None
    has_sdk: bool = False
    sdk_languages: list[str] = Field(default_factory=list)
    openapi_spec_url: str | None = None
    webhooks: bool = False


class EvaluationAuthSubmission(BaseModel):
    methods: list[str] = Field(default_factory=list)
    oauth: bool = False
    scopes: bool = False
    notes: str | None = Field(None, max_length=2000)

    @field_validator("methods", mode="before")
    @classmethod
    def cap_methods_list(cls, v):
        if not isinstance(v, list):
            return v
        return [str(item)[:200] for item in v[:20]]


class EvaluationPricingSubmission(BaseModel):
    model: str | None = Field(None, max_length=100)
    free_tier_exists: bool = False
    free_tier_limits: dict | None = None
    paid_tiers: list[dict] | None = None
    requires_credit_card: bool = False
    estimated_workload_costs: dict | None = None
    notes: str | None = Field(None, max_length=2000)


class EvaluationPerformanceSubmission(BaseModel):
    latency_p50_ms: int | None = None
    latency_p99_ms: int | None = None
    uptime_sla_percent: float | None = None
    rate_limits: dict | None = None
    data_source: str | None = None
    measured_on: str | None = None


class EvaluationRequirementsSubmission(BaseModel):
    requires_signup: bool = False
    requires_credit_card: bool = False
    domain_verification: bool = False
    data_residency: list[str] = Field(default_factory=list)
    compliance: list[str] = Field(default_factory=list)
    min_contract: str | None = "none"


class EvaluationAgentReadinessSubmission(BaseModel):
    mcp_server_quality: float | None = None
    documentation_accuracy: float | None = None
    error_message_quality: float | None = None
    error_message_notes: str | None = Field(None, max_length=1000)
    idempotency_support: str | None = None
    idempotency_notes: str | None = Field(None, max_length=1000)
    pagination_style: str | None = Field(None, max_length=50)
    retry_guidance_documented: bool | None = None
    known_agent_gotchas: list[str] = Field(default_factory=list)

    @field_validator("known_agent_gotchas", mode="before")
    @classmethod
    def cap_gotchas_list(cls, v):
        if not isinstance(v, list):
            return v
        return [str(item)[:500] for item in v[:50]]


class AFScoreComponentsSubmission(BaseModel):
    mcp_score: float = Field(ge=0, le=100)
    api_doc_score: float = Field(ge=0, le=100)
    error_handling_score: float = Field(ge=0, le=100)
    auth_complexity_score: float = Field(ge=0, le=100)
    rate_limit_clarity_score: float = Field(ge=0, le=100)


class SecurityScoreComponentsSubmission(BaseModel):
    tls_enforcement: float = Field(ge=0, le=100)
    auth_strength: float = Field(ge=0, le=100)
    scope_granularity: float = Field(ge=0, le=100)
    dependency_hygiene: float = Field(ge=0, le=100)
    secret_handling: float = Field(ge=0, le=100)
    security_notes: str | None = Field(None, max_length=2000)


class ReliabilityScoreComponentsSubmission(BaseModel):
    uptime_documented: float = Field(ge=0, le=100)
    version_stability: float = Field(ge=0, le=100)
    breaking_changes_history: float = Field(ge=0, le=100)
    error_recovery: float = Field(ge=0, le=100)


class SubComponentEvidence(BaseModel):
    """Evidence for a single sub-component score."""
    checkpoints: dict[str, bool] = Field(
        description="Map of checkpoint_id -> met (true/false)",
    )
    notes: str | None = Field(None, max_length=2000, description="Optional notes explaining the assessment")


class EvaluationEvidence(BaseModel):
    """Evidence checkpoints for rubric v2 submissions.

    Keys are sub-component IDs (e.g., 'api_doc_score', 'tls_enforcement').
    Only sub-components with scores need evidence entries.
    """
    # AF sub-components
    mcp_score: SubComponentEvidence | None = None
    api_doc_score: SubComponentEvidence | None = None
    error_handling_score: SubComponentEvidence | None = None
    auth_complexity_score: SubComponentEvidence | None = None
    rate_limit_clarity_score: SubComponentEvidence | None = None
    # Security sub-components
    tls_enforcement: SubComponentEvidence | None = None
    auth_strength: SubComponentEvidence | None = None
    scope_granularity: SubComponentEvidence | None = None
    dependency_hygiene: SubComponentEvidence | None = None
    secret_handling: SubComponentEvidence | None = None
    # Reliability sub-components
    uptime_documented: SubComponentEvidence | None = None
    version_stability: SubComponentEvidence | None = None
    breaking_changes_history: SubComponentEvidence | None = None
    error_recovery: SubComponentEvidence | None = None


class EvaluationSubmission(BaseModel):
    """Full evaluation submission matching the loader's expected JSON."""
    id: str = Field(max_length=200, description="Package ID (slug, e.g. 'stripe')")
    name: str = Field(max_length=200, description="Display name")
    evaluator_engine: str | None = Field(
        None, max_length=100, description="AI engine used for evaluation (e.g. 'claude', 'gpt-4', 'gemini')",
    )
    rubric_version: str = Field(
        "1.0", max_length=20, description="Rubric version used for this evaluation",
    )
    homepage: str | None = Field(None, max_length=2000)
    repo_url: str | None = Field(None, max_length=2000)
    category: str | None = Field(
        None, max_length=100, description="Category slug (normalized to canonical list)",
    )
    subcategories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    what_it_does: str | None = Field(None, max_length=2000)
    use_cases: list[str] = Field(default_factory=list)
    not_for: list[str] = Field(default_factory=list)
    best_when: str | None = Field(None, max_length=1000)
    avoid_when: str | None = Field(None, max_length=1000)
    alternatives: list[str] = Field(default_factory=list)
    version_evaluated: str | None = Field(None, max_length=100)
    interface: EvaluationInterfaceSubmission | None = None
    auth: EvaluationAuthSubmission | None = None
    pricing: EvaluationPricingSubmission | None = None
    performance: EvaluationPerformanceSubmission | None = None
    requirements: EvaluationRequirementsSubmission | None = None
    agent_readiness: EvaluationAgentReadinessSubmission | None = None
    af_score_components: AFScoreComponentsSubmission | None = None
    security_score_components: SecurityScoreComponentsSubmission | None = None
    reliability_score_components: ReliabilityScoreComponentsSubmission | None = None
    evidence: EvaluationEvidence | None = Field(
        None,
        description="Evidence checkpoints (required for rubric_version 2.0+, optional for 1.0)",
    )

    @field_validator("use_cases", "not_for", "alternatives", "tags", "subcategories", mode="before")
    @classmethod
    def cap_string_lists(cls, v):
        if not isinstance(v, list):
            return v
        return [str(item)[:500] for item in v[:50]]


class EvaluationSubmissionResponse(BaseModel):
    status: str = Field(description="'accepted' or 'pending_review'")
    package_id: str = Field(description="Package ID that was submitted")
    message: str = Field(description="Human-readable status message")


class PendingEvaluationResponse(BaseModel):
    id: int = Field(description="Pending evaluation ID")
    package_id: str = Field(description="Package slug")
    submitted_at: str = Field(description="ISO 8601 timestamp")
    submitted_by: str | None = Field(None, description="API key identifier")
    status: str = Field(description="pending, approved, or rejected")


class PendingEvaluationListResponse(BaseModel):
    evaluations: list[PendingEvaluationResponse] = Field(default_factory=list)
    total: int = Field(description="Total pending evaluations")
