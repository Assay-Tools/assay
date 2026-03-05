"""Tests for web features: badges, RSS feed, developer docs."""


class TestScoreBadges:
    def test_badge_evaluated_package(self, client, sample_packages):
        resp = client.get("/badge/top-api.svg")
        assert resp.status_code == 200
        assert "image/svg+xml" in resp.headers["content-type"]
        assert "92" in resp.text

    def test_badge_nonexistent_package(self, client):
        resp = client.get("/badge/nonexistent.svg")
        assert resp.status_code == 200
        assert "not found" in resp.text

    def test_badge_color_green(self, client, sample_packages):
        """Packages with AF >= 80 get green badge."""
        resp = client.get("/badge/top-api.svg")
        assert "#4c1" in resp.text  # green

    def test_badge_color_yellow(self, client, sample_packages):
        """Packages with AF 60-79 get yellow badge."""
        resp = client.get("/badge/mid-tool.svg")
        assert "#dfb317" in resp.text  # yellow

    def test_badge_color_red(self, client, sample_packages):
        """Packages with AF < 60 get red badge."""
        resp = client.get("/badge/low-sdk.svg")
        assert "#e05d44" in resp.text  # red

    def test_badge_cache_header(self, client, sample_packages):
        """Badge response includes cache headers."""
        resp = client.get("/badge/top-api.svg")
        assert "max-age=3600" in resp.headers.get("cache-control", "")


class TestRSSFeed:
    def test_rss_returns_xml(self, client, sample_packages):
        resp = client.get("/feed.xml")
        assert resp.status_code == 200
        assert "application/rss+xml" in resp.headers["content-type"]
        assert "<rss" in resp.text

    def test_rss_contains_packages(self, client, sample_packages):
        resp = client.get("/feed.xml")
        assert "Top API" in resp.text
        assert "assay.tools/packages/top-api" in resp.text

    def test_rss_excludes_unevaluated(self, client, sample_packages):
        resp = client.get("/feed.xml")
        assert "new-pkg" not in resp.text


class TestDeveloperDocs:
    def test_developers_page(self, client):
        resp = client.get("/developers")
        assert resp.status_code == 200
        assert "Developer Documentation" in resp.text
        assert "/v1/packages" in resp.text
        assert "Rate Limits" in resp.text
        assert "MCP Server" in resp.text


class TestMethodologyPage:
    def test_methodology_page(self, client):
        resp = client.get("/methodology")
        assert resp.status_code == 200
        assert "Scoring Methodology" in resp.text
        assert "Agent Friendliness" in resp.text
        assert "Security" in resp.text
        assert "Reliability" in resp.text

    def test_methodology_shows_weights(self, client):
        resp = client.get("/methodology")
        assert "25%" in resp.text
        assert "20%" in resp.text
        assert "15%" in resp.text

    def test_methodology_shows_limitations(self, client):
        resp = client.get("/methodology")
        assert "Limitations" in resp.text
        assert "Point-in-time snapshots" in resp.text


class TestEmbedCompare:
    def test_embed_compare(self, client, sample_packages):
        resp = client.get("/embed/compare?ids=top-api,mid-tool")
        assert resp.status_code == 200
        assert "Top API" in resp.text
        assert "Mid Tool" in resp.text
        assert "assay.tools" in resp.text

    def test_embed_compare_single(self, client, sample_packages):
        resp = client.get("/embed/compare?ids=top-api")
        assert resp.status_code == 200
        assert "92" in resp.text

    def test_embed_no_base_template(self, client, sample_packages):
        """Embed should be self-contained, not using base.html."""
        resp = client.get("/embed/compare?ids=top-api")
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text
        # Should NOT contain base template elements like nav
        assert "Search packages" not in resp.text
