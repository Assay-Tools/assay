"""Pydantic response models for the Assay API."""

from pydantic import BaseModel, Field

# --- Health ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


# --- Packages ---

class PackageListResponse(BaseModel):
    packages: list[dict] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class PackageSingleResponse(BaseModel):
    """Wraps a full Package.to_dict() result."""
    # Using dict since the shape is dynamic (optional sub-objects)
    model_config = {"extra": "allow"}


class AgentGuideResponse(BaseModel):
    """Wraps a Package.to_agent_guide() result."""
    model_config = {"extra": "allow"}


# --- Categories ---

class CategoryItem(BaseModel):
    slug: str
    name: str
    description: str | None = None
    package_count: int = 0


class CategoryListResponse(BaseModel):
    categories: list[CategoryItem] = Field(default_factory=list)


class CategoryPackagesResponse(BaseModel):
    category: CategoryItem
    packages: list[dict] = Field(default_factory=list)


# --- Compare ---

class CompareResponse(BaseModel):
    packages: list[dict] = Field(default_factory=list)


# --- Stats ---

class ScoreDistribution(BaseModel):
    excellent: int = Field(description="AF score >= 8.0")
    good: int = Field(description="AF score >= 6.0 and < 8.0")
    fair: int = Field(description="AF score >= 4.0 and < 6.0")
    poor: int = Field(description="AF score < 4.0")
    unrated: int = Field(description="No AF score")


class StatsResponse(BaseModel):
    total_packages: int
    total_evaluated: int = 0
    total_categories: int
    avg_af_score: float | None
    score_distribution: ScoreDistribution
