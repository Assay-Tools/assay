"""Package data models — the core of Assay."""

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assay.database import Base


class Package(Base):
    """Core package record."""

    __tablename__ = "packages"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # e.g., "resend"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    homepage: Mapped[str | None] = mapped_column(String(512))
    repo_url: Mapped[str | None] = mapped_column(String(512))
    category_slug: Mapped[str | None] = mapped_column(String(100), ForeignKey("categories.slug"))
    subcategories: Mapped[str | None] = mapped_column(Text)  # JSON array
    tags: Mapped[str | None] = mapped_column(Text)  # JSON array

    # Core descriptive fields
    what_it_does: Mapped[str | None] = mapped_column(Text)
    use_cases: Mapped[str | None] = mapped_column(Text)  # JSON array
    not_for: Mapped[str | None] = mapped_column(Text)  # JSON array
    best_when: Mapped[str | None] = mapped_column(Text)
    avoid_when: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[str | None] = mapped_column(Text)  # JSON array

    # Scores
    af_score: Mapped[float | None] = mapped_column(Float)
    fq_score: Mapped[float | None] = mapped_column(Float)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="discovered")  # discovered, evaluated, published
    version_evaluated: Mapped[str | None] = mapped_column(String(100))
    last_evaluated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category: Mapped["Category | None"] = relationship(back_populates="packages")
    interface: Mapped["PackageInterface | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    auth: Mapped["PackageAuth | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    pricing: Mapped["PackagePricing | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    performance: Mapped["PackagePerformance | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    requirements: Mapped["PackageRequirements | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    agent_readiness: Mapped["PackageAgentReadiness | None"] = relationship(
        back_populates="package", uselist=False, cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["EvaluationRun"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )

    def _json_field(self, field_name: str) -> list | dict | None:
        val = getattr(self, field_name)
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val

    @property
    def use_cases_list(self) -> list[str]:
        return self._json_field("use_cases") or []

    @property
    def not_for_list(self) -> list[str]:
        return self._json_field("not_for") or []

    @property
    def tags_list(self) -> list[str]:
        return self._json_field("tags") or []

    @property
    def subcategories_list(self) -> list[str]:
        return self._json_field("subcategories") or []

    @property
    def alternatives_list(self) -> list[str]:
        return self._json_field("alternatives") or []

    def to_dict(self) -> dict:
        """Full package record as dict."""
        result = {
            "id": self.id,
            "name": self.name,
            "homepage": self.homepage,
            "repo_url": self.repo_url,
            "category": self.category_slug,
            "subcategories": self.subcategories_list,
            "tags": self.tags_list,
            "what_it_does": self.what_it_does,
            "use_cases": self.use_cases_list,
            "not_for": self.not_for_list,
            "best_when": self.best_when,
            "avoid_when": self.avoid_when,
            "alternatives": self.alternatives_list,
            "af_score": self.af_score,
            "fq_score": self.fq_score,
            "status": self.status,
            "version_evaluated": self.version_evaluated,
            "last_evaluated": self.last_evaluated.isoformat() if self.last_evaluated else None,
        }
        if self.interface:
            result["interface"] = self.interface.to_dict()
        if self.auth:
            result["auth"] = self.auth.to_dict()
        if self.pricing:
            result["pricing"] = self.pricing.to_dict()
        if self.performance:
            result["performance"] = self.performance.to_dict()
        if self.requirements:
            result["requirements"] = self.requirements.to_dict()
        if self.agent_readiness:
            result["agent_readiness"] = self.agent_readiness.to_dict()
        return result

    def to_agent_guide(self) -> dict:
        """Condensed agent-optimized view — key fields only."""
        result = {
            "id": self.id,
            "name": self.name,
            "af_score": self.af_score,
            "what_it_does": self.what_it_does,
            "best_when": self.best_when,
            "avoid_when": self.avoid_when,
        }
        if self.interface:
            result["has_mcp"] = self.interface.has_mcp_server
            result["has_api"] = self.interface.has_rest_api
        if self.auth:
            result["auth_methods"] = self.auth.methods_list
        if self.pricing:
            result["has_free_tier"] = self.pricing.free_tier_exists
        if self.agent_readiness:
            result["known_gotchas"] = self.agent_readiness.gotchas_list
            result["error_quality"] = self.agent_readiness.error_message_quality
        return result


class PackageInterface(Base):
    """How to connect to the package."""

    __tablename__ = "package_interfaces"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    has_rest_api: Mapped[bool] = mapped_column(Boolean, default=False)
    has_graphql: Mapped[bool] = mapped_column(Boolean, default=False)
    has_grpc: Mapped[bool] = mapped_column(Boolean, default=False)
    has_mcp_server: Mapped[bool] = mapped_column(Boolean, default=False)
    mcp_server_url: Mapped[str | None] = mapped_column(String(512))
    has_sdk: Mapped[bool] = mapped_column(Boolean, default=False)
    sdk_languages: Mapped[str | None] = mapped_column(Text)  # JSON array
    openapi_spec_url: Mapped[str | None] = mapped_column(String(512))
    webhooks: Mapped[bool] = mapped_column(Boolean, default=False)

    package: Mapped["Package"] = relationship(back_populates="interface")

    def to_dict(self) -> dict:
        return {
            "has_rest_api": self.has_rest_api,
            "has_graphql": self.has_graphql,
            "has_grpc": self.has_grpc,
            "has_mcp_server": self.has_mcp_server,
            "mcp_server_url": self.mcp_server_url,
            "has_sdk": self.has_sdk,
            "sdk_languages": json.loads(self.sdk_languages) if self.sdk_languages else [],
            "openapi_spec_url": self.openapi_spec_url,
            "webhooks": self.webhooks,
        }


class PackageAuth(Base):
    """Authentication requirements."""

    __tablename__ = "package_auth"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    methods: Mapped[str | None] = mapped_column(Text)  # JSON array: ["api_key", "oauth2"]
    oauth: Mapped[bool] = mapped_column(Boolean, default=False)
    scopes: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    package: Mapped["Package"] = relationship(back_populates="auth")

    @property
    def methods_list(self) -> list[str]:
        return json.loads(self.methods) if self.methods else []

    def to_dict(self) -> dict:
        return {
            "methods": self.methods_list,
            "oauth": self.oauth,
            "scopes": self.scopes,
            "notes": self.notes,
        }


class PackagePricing(Base):
    """Pricing and cost information."""

    __tablename__ = "package_pricing"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    model: Mapped[str | None] = mapped_column(String(50))  # free, freemium, paid, usage_based, open_source
    free_tier_exists: Mapped[bool] = mapped_column(Boolean, default=False)
    free_tier_limits: Mapped[str | None] = mapped_column(Text)  # JSON object
    paid_tiers: Mapped[str | None] = mapped_column(Text)  # JSON array
    requires_credit_card: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_workload_costs: Mapped[str | None] = mapped_column(Text)  # JSON object
    notes: Mapped[str | None] = mapped_column(Text)

    package: Mapped["Package"] = relationship(back_populates="pricing")

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "free_tier_exists": self.free_tier_exists,
            "free_tier_limits": json.loads(self.free_tier_limits) if self.free_tier_limits else None,
            "paid_tiers": json.loads(self.paid_tiers) if self.paid_tiers else [],
            "requires_credit_card": self.requires_credit_card,
            "estimated_workload_costs": json.loads(self.estimated_workload_costs)
            if self.estimated_workload_costs
            else None,
            "notes": self.notes,
        }


class PackagePerformance(Base):
    """Performance and reliability data."""

    __tablename__ = "package_performance"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    latency_p50_ms: Mapped[int | None] = mapped_column(Integer)
    latency_p99_ms: Mapped[int | None] = mapped_column(Integer)
    uptime_sla_percent: Mapped[float | None] = mapped_column(Float)
    rate_limits: Mapped[str | None] = mapped_column(Text)  # JSON object
    data_source: Mapped[str | None] = mapped_column(String(100))  # "synthetic_monitoring", "documented", "estimated"
    measured_on: Mapped[str | None] = mapped_column(String(20))

    package: Mapped["Package"] = relationship(back_populates="performance")

    def to_dict(self) -> dict:
        return {
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "uptime_sla_percent": self.uptime_sla_percent,
            "rate_limits": json.loads(self.rate_limits) if self.rate_limits else None,
            "data_source": self.data_source,
            "measured_on": self.measured_on,
        }


class PackageRequirements(Base):
    """Setup requirements and compliance."""

    __tablename__ = "package_requirements"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    requires_signup: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_credit_card: Mapped[bool] = mapped_column(Boolean, default=False)
    domain_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    data_residency: Mapped[str | None] = mapped_column(Text)  # JSON array: ["US", "EU"]
    compliance: Mapped[str | None] = mapped_column(Text)  # JSON array: ["SOC2", "HIPAA"]
    min_contract: Mapped[str | None] = mapped_column(String(50))  # "none", "monthly", "annual"

    package: Mapped["Package"] = relationship(back_populates="requirements")

    def to_dict(self) -> dict:
        return {
            "requires_signup": self.requires_signup,
            "requires_credit_card": self.requires_credit_card,
            "domain_verification": self.domain_verification,
            "data_residency": json.loads(self.data_residency) if self.data_residency else [],
            "compliance": json.loads(self.compliance) if self.compliance else [],
            "min_contract": self.min_contract,
        }


class PackageAgentReadiness(Base):
    """Agent-friendliness scoring and metadata."""

    __tablename__ = "package_agent_readiness"

    package_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("packages.id"), primary_key=True
    )
    af_score: Mapped[float | None] = mapped_column(Float)
    mcp_server_quality: Mapped[float | None] = mapped_column(Float)
    mcp_security_score: Mapped[float | None] = mapped_column(Float)
    documentation_accuracy: Mapped[float | None] = mapped_column(Float)
    error_message_quality: Mapped[str | None] = mapped_column(String(50))  # "good", "poor", "unknown"
    error_message_notes: Mapped[str | None] = mapped_column(Text)
    idempotency_support: Mapped[bool | None] = mapped_column(Boolean)
    idempotency_notes: Mapped[str | None] = mapped_column(Text)
    pagination_style: Mapped[str | None] = mapped_column(String(50))  # "cursor", "offset", "none"
    retry_guidance_documented: Mapped[bool | None] = mapped_column(Boolean)
    known_agent_gotchas: Mapped[str | None] = mapped_column(Text)  # JSON array

    package: Mapped["Package"] = relationship(back_populates="agent_readiness")

    @property
    def gotchas_list(self) -> list[str]:
        return json.loads(self.known_agent_gotchas) if self.known_agent_gotchas else []

    def to_dict(self) -> dict:
        return {
            "af_score": self.af_score,
            "mcp_server_quality": self.mcp_server_quality,
            "mcp_security_score": self.mcp_security_score,
            "documentation_accuracy": self.documentation_accuracy,
            "error_message_quality": self.error_message_quality,
            "error_message_notes": self.error_message_notes,
            "idempotency_support": self.idempotency_support,
            "idempotency_notes": self.idempotency_notes,
            "pagination_style": self.pagination_style,
            "retry_guidance_documented": self.retry_guidance_documented,
            "known_agent_gotchas": self.gotchas_list,
        }


class Category(Base):
    """Package categories."""

    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    packages: Mapped[list["Package"]] = relationship(back_populates="category")

    @property
    def package_count(self) -> int:
        return len(self.packages)

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "package_count": self.package_count,
        }


class EvaluationRun(Base):
    """Record of each evaluation run for audit trail."""

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_id: Mapped[str] = mapped_column(String(255), ForeignKey("packages.id"))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    model_used: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    raw_output: Mapped[str | None] = mapped_column(Text)  # Full LLM response for audit
    af_score_computed: Mapped[float | None] = mapped_column(Float)

    package: Mapped["Package"] = relationship(back_populates="evaluations")
