"""Tests for category-related API endpoints."""


class TestListCategories:
    def test_empty_db(self, client):
        resp = client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["categories"] == []

    def test_returns_categories(self, client, sample_packages):
        resp = client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        slugs = {c["slug"] for c in data["categories"]}
        assert "developer-tools" in slugs
        assert "ai-ml" in slugs

    def test_category_package_count(self, client, sample_packages):
        resp = client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        by_slug = {c["slug"]: c for c in data["categories"]}

        # developer-tools: top-api (92), mid-tool (68), new-pkg (None) → count=2 (evaluated only)
        assert by_slug["developer-tools"]["package_count"] == 2

        # ai-ml: basic-sdk (52), legacy-api (30) → count=2
        assert by_slug["ai-ml"]["package_count"] == 2

    def test_categories_sorted_by_name(self, client, sample_packages):
        resp = client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data["categories"]]
        assert names == sorted(names)


class TestCategoryPackages:
    def test_get_category_packages(self, client, sample_packages):
        resp = client.get("/v1/categories/developer-tools/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"]["slug"] == "developer-tools"
        assert len(data["packages"]) == 3  # includes unevaluated

    def test_category_packages_sorted_by_af_score(self, client, sample_packages):
        resp = client.get("/v1/categories/developer-tools/packages")
        assert resp.status_code == 200
        data = resp.json()
        scored = [p for p in data["packages"] if p["af_score"] is not None]
        scores = [p["af_score"] for p in scored]
        assert scores == sorted(scores, reverse=True)

    def test_nonexistent_category(self, client):
        resp = client.get("/v1/categories/nonexistent/packages")
        assert resp.status_code == 404
