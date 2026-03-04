"""Pydantic response models for the Assay API."""

from pydantic import BaseModel, Field

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
