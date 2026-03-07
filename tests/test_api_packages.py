"""Tests for package-related API endpoints."""


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestListPackages:
    def test_empty_db(self, client):
        resp = client.get("/v1/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["packages"] == []
        assert data["total"] == 0

    def test_returns_packages(self, client, sample_packages):
        resp = client.get("/v1/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6  # all packages including unevaluated

    def test_filter_by_category(self, client, sample_packages):
        resp = client.get("/v1/packages?category=ai-ml")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        names = {p["name"] for p in data["packages"]}
        assert "Basic SDK" in names
        assert "Legacy API" in names
        assert "Low SDK" in names

    def test_filter_by_min_af_score(self, client, sample_packages):
        resp = client.get("/v1/packages?min_af_score=80")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["packages"][0]["name"] == "Top API"

    def test_filter_by_package_type(self, client, sample_packages):
        resp = client.get("/v1/packages?type=mcp_server")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6

    def test_sort_af_score_desc(self, client, sample_packages):
        resp = client.get("/v1/packages?sort=af_score:desc")
        assert resp.status_code == 200
        data = resp.json()
        scores = [p["af_score"] for p in data["packages"] if p["af_score"] is not None]
        assert scores == sorted(scores, reverse=True)

    def test_sort_af_score_asc(self, client, sample_packages):
        resp = client.get("/v1/packages?sort=af_score:asc")
        assert resp.status_code == 200
        data = resp.json()
        # Null scores should be present but order of non-null should be ascending
        scores = [p["af_score"] for p in data["packages"] if p["af_score"] is not None]
        assert scores == sorted(scores)

    def test_sort_by_name(self, client, sample_packages):
        resp = client.get("/v1/packages?sort=name:asc")
        assert resp.status_code == 200
        data = resp.json()
        names = [p["name"] for p in data["packages"]]
        assert names == sorted(names)

    def test_invalid_sort_field(self, client, sample_packages):
        resp = client.get("/v1/packages?sort=nonexistent:asc")
        assert resp.status_code == 400

    def test_pagination_limit(self, client, sample_packages):
        resp = client.get("/v1/packages?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 2
        assert data["total"] == 6
        assert data["limit"] == 2

    def test_pagination_offset(self, client, sample_packages):
        resp = client.get("/v1/packages?limit=2&offset=2&sort=name:asc")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 2
        assert data["offset"] == 2

    def test_filter_has_mcp(self, client, sample_packages):
        resp = client.get("/v1/packages?has_mcp=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["packages"][0]["name"] == "Top API"


class TestSearchPackages:
    def test_search_with_q(self, client, sample_packages):
        resp = client.get("/v1/packages?q=Top")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = {p["name"] for p in data["packages"]}
        assert "Top API" in names

    def test_search_with_search_alias(self, client, sample_packages):
        resp = client.get("/v1/packages?search=Top")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_search_no_results(self, client, sample_packages):
        resp = client.get("/v1/packages?q=zzzznonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["packages"] == []


class TestGetPackage:
    def test_get_existing_package(self, client, sample_packages):
        resp = client.get("/v1/packages/top-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "top-api"
        assert data["name"] == "Top API"
        assert data["af_score"] == 92.0

    def test_get_nonexistent_package(self, client):
        resp = client.get("/v1/packages/nonexistent")
        assert resp.status_code == 404

    def test_package_includes_relationships(self, client, sample_packages):
        resp = client.get("/v1/packages/top-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["interface"]["has_rest_api"] is True
        assert data["interface"]["has_mcp_server"] is True
        assert data["agent_readiness"]["documentation_accuracy"] == 95.0


class TestGetAgentGuide:
    def test_agent_guide(self, client, sample_packages):
        resp = client.get("/v1/packages/top-api/agent-guide")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "top-api"
        assert data["af_score"] == 92.0
        assert "has_mcp" in data
        assert "has_api" in data

    def test_agent_guide_nonexistent(self, client):
        resp = client.get("/v1/packages/nonexistent/agent-guide")
        assert resp.status_code == 404


class TestFilterByScoreDimension:
    def test_min_security_score(self, client, sample_packages):
        resp = client.get("/v1/packages?min_security_score=60")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {p["name"] for p in data["packages"]}
        assert names == {"Top API", "Mid Tool"}

    def test_min_reliability_score(self, client, sample_packages):
        resp = client.get("/v1/packages?min_reliability_score=70")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {p["name"] for p in data["packages"]}
        assert names == {"Top API", "Mid Tool"}

    def test_combined_score_filters(self, client, sample_packages):
        resp = client.get(
            "/v1/packages?min_security_score=80&min_reliability_score=80"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["packages"][0]["name"] == "Top API"

    def test_score_filter_excludes_null(self, client, sample_packages):
        """Packages with NULL scores should not match any minimum filter."""
        resp = client.get("/v1/packages?min_security_score=0")
        assert resp.status_code == 200
        data = resp.json()
        # new-pkg has None scores, should be excluded
        names = {p["name"] for p in data["packages"]}
        assert "New Package" not in names

    def test_score_filter_with_category(self, client, sample_packages):
        resp = client.get(
            "/v1/packages?category=ai-ml&min_security_score=30"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {p["name"] for p in data["packages"]}
        assert "Basic SDK" in names
        assert "Low SDK" in names


class TestUpdatedSince:
    def test_updated_since_returns_recent(self, client, sample_packages):
        """All sample packages were just created, so a past timestamp returns all."""
        resp = client.get(
            "/v1/packages/updated-since?timestamp=2020-01-01T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6

    def test_updated_since_future_returns_none(self, client, sample_packages):
        resp = client.get(
            "/v1/packages/updated-since?timestamp=2099-01-01T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["packages"] == []

    def test_updated_since_invalid_timestamp(self, client):
        resp = client.get(
            "/v1/packages/updated-since?timestamp=not-a-date"
        )
        assert resp.status_code == 400

    def test_updated_since_pagination(self, client, sample_packages):
        resp = client.get(
            "/v1/packages/updated-since?timestamp=2020-01-01T00:00:00Z&limit=2&offset=0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 2
        assert data["total"] == 6

    def test_updated_since_requires_timestamp(self, client):
        resp = client.get("/v1/packages/updated-since")
        assert resp.status_code == 400  # Missing 'since' parameter

    def test_updated_since_accepts_since_param(self, client, sample_packages):
        resp = client.get(
            "/v1/packages/updated-since?since=2020-01-01T00:00:00Z&limit=2"
        )
        assert resp.status_code == 200
        assert len(resp.json()["packages"]) == 2
