"""Shared fixtures for Assay test suite."""

import os

# Override database URL BEFORE importing the app module (which creates the engine at import time)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from assay.database import Base, get_db
from assay.api.app import app
from assay.models.package import (
    Category,
    Package,
    PackageAgentReadiness,
    PackageAuth,
    PackageInterface,
    PackagePerformance,
    PackagePricing,
    PackageRequirements,
)


@pytest.fixture()
def db_engine(tmp_path):
    """SQLite test database in a temp directory."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(db_engine):
    """Database session for direct model testing."""
    TestSession = sessionmaker(bind=db_engine, class_=Session, expire_on_commit=False)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def client(db_engine):
    """FastAPI TestClient with test database.

    Overrides both the FastAPI get_db dependency AND the module-level engine
    used by startup migrations, so everything uses the test database.
    """
    import assay.database as db_module

    TestSession = sessionmaker(bind=db_engine, class_=Session, expire_on_commit=False)

    def _override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    # Swap the module-level engine so startup() and _run_migrations() use test DB
    original_engine = db_module.engine
    db_module.engine = db_engine

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db_module.engine = original_engine


# --- Factory fixtures ---


@pytest.fixture()
def make_category(db):
    """Factory for creating test categories."""
    created = []

    def _make(slug: str = "test-cat", name: str = "Test Category", description: str = None):
        cat = Category(slug=slug, name=name, description=description)
        db.add(cat)
        db.commit()
        created.append(cat)
        return cat

    return _make


@pytest.fixture()
def make_package(db, make_category):
    """Factory for creating test packages with optional related objects."""

    def _make(
        id: str = "test-pkg",
        name: str = "Test Package",
        category_slug: str = "test-cat",
        af_score: float | None = 75.0,
        security_score: float | None = 70.0,
        reliability_score: float | None = 72.0,
        what_it_does: str = "A test package",
        status: str = "evaluated",
        package_type: str = "mcp_server",
        **kwargs,
    ):
        # Ensure category exists
        if category_slug and not db.query(Category).filter(Category.slug == category_slug).first():
            make_category(slug=category_slug, name=category_slug.replace("-", " ").title())

        pkg = Package(
            id=id,
            name=name,
            category_slug=category_slug,
            af_score=af_score,
            security_score=security_score,
            reliability_score=reliability_score,
            what_it_does=what_it_does,
            status=status,
            package_type=package_type,
            **kwargs,
        )
        db.add(pkg)
        db.commit()
        return pkg

    return _make


@pytest.fixture()
def make_interface(db):
    """Factory for creating package interface records."""

    def _make(package_id: str, **kwargs):
        defaults = {
            "has_rest_api": False,
            "has_graphql": False,
            "has_grpc": False,
            "has_mcp_server": False,
            "has_sdk": False,
            "webhooks": False,
        }
        defaults.update(kwargs)
        iface = PackageInterface(package_id=package_id, **defaults)
        db.add(iface)
        db.commit()
        return iface

    return _make


@pytest.fixture()
def make_auth(db):
    """Factory for creating package auth records."""

    def _make(package_id: str, **kwargs):
        auth = PackageAuth(package_id=package_id, **kwargs)
        db.add(auth)
        db.commit()
        return auth

    return _make


@pytest.fixture()
def make_agent_readiness(db):
    """Factory for creating agent readiness records."""

    def _make(package_id: str, **kwargs):
        ar = PackageAgentReadiness(package_id=package_id, **kwargs)
        db.add(ar)
        db.commit()
        return ar

    return _make


@pytest.fixture()
def make_pricing(db):
    """Factory for creating package pricing records."""

    def _make(package_id: str, **kwargs):
        pricing = PackagePricing(package_id=package_id, **kwargs)
        db.add(pricing)
        db.commit()
        return pricing

    return _make


# --- Pre-built test data ---


@pytest.fixture()
def sample_packages(make_package, make_interface, make_auth, make_agent_readiness):
    """Create a realistic set of test packages across categories."""
    pkgs = []

    # Excellent package
    p1 = make_package(
        id="top-api",
        name="Top API",
        category_slug="developer-tools",
        af_score=92.0,
        security_score=90.0,
        reliability_score=88.0,
    )
    make_interface(p1.id, has_rest_api=True, has_mcp_server=True)
    make_auth(p1.id, methods='["api_key"]')
    make_agent_readiness(
        p1.id,
        af_score=92.0,
        documentation_accuracy=95.0,
        error_message_quality=90.0,
        mcp_server_quality=88.0,
        tls_enforcement=100.0,
        auth_strength=90.0,
    )
    pkgs.append(p1)

    # Good package
    p2 = make_package(
        id="mid-tool",
        name="Mid Tool",
        category_slug="developer-tools",
        af_score=68.0,
        security_score=65.0,
        reliability_score=70.0,
    )
    make_interface(p2.id, has_rest_api=True)
    make_agent_readiness(p2.id, af_score=68.0, documentation_accuracy=72.0)
    pkgs.append(p2)

    # Fair package
    p3 = make_package(
        id="basic-sdk",
        name="Basic SDK",
        category_slug="ai-ml",
        af_score=52.0,
        security_score=48.0,
        reliability_score=55.0,
    )
    pkgs.append(p3)

    # Poor package
    p4 = make_package(
        id="legacy-api",
        name="Legacy API",
        category_slug="ai-ml",
        af_score=30.0,
        security_score=25.0,
        reliability_score=35.0,
    )
    pkgs.append(p4)

    # Unevaluated package
    p5 = make_package(
        id="new-pkg",
        name="New Package",
        category_slug="developer-tools",
        af_score=None,
        security_score=None,
        reliability_score=None,
        status="discovered",
    )
    pkgs.append(p5)

    return pkgs
