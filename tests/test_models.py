"""Tests for Assay SQLAlchemy models."""


from assay.models.package import Category


class TestCategory:
    def test_create_category(self, make_category):
        cat = make_category(slug="dev-tools", name="Developer Tools", description="Tools for devs")
        assert cat.slug == "dev-tools"
        assert cat.name == "Developer Tools"
        assert cat.description == "Tools for devs"

    def test_package_count_only_evaluated(self, db, make_category, make_package):
        """package_count should only count packages with af_score != None."""
        make_category(slug="mixed", name="Mixed")
        make_package(id="eval-1", name="Eval 1", category_slug="mixed", af_score=75.0)
        make_package(id="eval-2", name="Eval 2", category_slug="mixed", af_score=60.0)
        make_package(id="uneval", name="Uneval", category_slug="mixed", af_score=None)

        cat = db.query(Category).filter(Category.slug == "mixed").first()
        assert cat.package_count == 2  # not 3


class TestPackage:
    def test_create_package(self, make_package):
        pkg = make_package(id="my-pkg", name="My Package", af_score=85.0)
        assert pkg.id == "my-pkg"
        assert pkg.name == "My Package"
        assert pkg.af_score == 85.0

    def test_to_dict_basic(self, make_package):
        pkg = make_package(id="dict-test", name="Dict Test", af_score=70.0)
        d = pkg.to_dict()
        assert d["id"] == "dict-test"
        assert d["name"] == "Dict Test"
        assert d["af_score"] == 70.0
        # Relationships are omitted when no related record exists
        assert "category" in d

    def test_to_dict_with_interface(self, make_package, make_interface):
        pkg = make_package(id="iface-test", name="Iface Test")
        make_interface(pkg.id, has_rest_api=True, has_mcp_server=True)

        # Refresh to pick up relationship
        from sqlalchemy.orm import Session
        session = Session.object_session(pkg)
        session.refresh(pkg)

        d = pkg.to_dict()
        assert d["interface"]["has_rest_api"] is True
        assert d["interface"]["has_mcp_server"] is True

    def test_to_agent_guide(self, make_package, make_interface, make_auth):
        pkg = make_package(id="guide-test", name="Guide Test", af_score=80.0)
        make_interface(pkg.id, has_rest_api=True, has_mcp_server=False)
        make_auth(pkg.id, methods='["api_key", "oauth2"]')

        session = type(pkg).metadata  # noqa
        from sqlalchemy.orm import Session
        Session.object_session(pkg).refresh(pkg)

        guide = pkg.to_agent_guide()
        assert guide["id"] == "guide-test"
        assert guide["af_score"] == 80.0
        assert guide["has_api"] is True
        assert guide["has_mcp"] is False

    def test_json_list_properties(self, make_package):
        pkg = make_package(
            id="json-test",
            name="JSON Test",
            tags='["tag1", "tag2"]',
            use_cases='["Use case 1", "Use case 2"]',
            alternatives='["alt1", "alt2"]',
        )
        assert pkg.tags_list == ["tag1", "tag2"]
        assert pkg.use_cases_list == ["Use case 1", "Use case 2"]
        assert pkg.alternatives_list == ["alt1", "alt2"]

    def test_json_list_properties_empty(self, make_package):
        pkg = make_package(id="empty-json", name="Empty JSON")
        assert pkg.tags_list == []
        assert pkg.use_cases_list == []

    def test_null_scores(self, make_package):
        pkg = make_package(
            id="null-scores",
            name="Null Scores",
            af_score=None,
            security_score=None,
            reliability_score=None,
        )
        d = pkg.to_dict()
        assert d["af_score"] is None
        assert d["security_score"] is None
        assert d["reliability_score"] is None


class TestPackageAgentReadiness:
    def test_gotchas_list(self, make_package, make_agent_readiness):
        pkg = make_package(id="gotcha-test", name="Gotcha Test")
        make_agent_readiness(
            pkg.id,
            known_agent_gotchas='["Gotcha 1", "Gotcha 2"]',
        )

        from sqlalchemy.orm import Session
        Session.object_session(pkg).refresh(pkg)

        ar = pkg.agent_readiness
        assert ar.gotchas_list == ["Gotcha 1", "Gotcha 2"]

    def test_gotchas_list_empty(self, make_package, make_agent_readiness):
        pkg = make_package(id="no-gotcha", name="No Gotcha")
        make_agent_readiness(pkg.id)

        from sqlalchemy.orm import Session
        Session.object_session(pkg).refresh(pkg)

        assert pkg.agent_readiness.gotchas_list == []
