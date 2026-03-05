"""Tests for admin dashboard routes."""


class TestFreshnessDashboard:
    def test_freshness_returns_200(self, client):
        resp = client.get("/admin/freshness")
        assert resp.status_code == 200
        assert "Data Freshness" in resp.text

    def test_freshness_shows_counts(self, client, make_package):
        make_package(id="pkg-a", name="A", af_score=80.0)
        make_package(id="pkg-b", name="B", af_score=None)
        resp = client.get("/admin/freshness")
        # Should show 2 cataloged, 1 evaluated
        assert "2" in resp.text  # total cataloged
        assert "Evaluated" in resp.text

    def test_freshness_shows_category_breakdown(self, client, make_package):
        make_package(id="pkg-c", name="C", category_slug="ai-ml", af_score=70.0)
        resp = client.get("/admin/freshness")
        assert "Ai Ml" in resp.text or "ai-ml" in resp.text

    def test_freshness_shows_staleness_buckets(self, client):
        resp = client.get("/admin/freshness")
        assert "0-30 days" in resp.text
        assert "91-180 days" in resp.text
        assert "180+ days" in resp.text
