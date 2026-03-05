"""Tests for SEO routes — robots.txt, sitemap.xml, meta tags."""


class TestRobotsTxt:
    def test_robots_txt_returns_200(self, client):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "User-agent: *" in resp.text
        assert "Sitemap: https://assay.tools/sitemap.xml" in resp.text

    def test_robots_txt_content_type(self, client):
        resp = client.get("/robots.txt")
        assert "text/plain" in resp.headers["content-type"]


class TestSitemapXml:
    def test_sitemap_returns_xml(self, client):
        resp = client.get("/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert '<?xml version="1.0"' in resp.text
        assert "<urlset" in resp.text

    def test_sitemap_contains_static_pages(self, client):
        resp = client.get("/sitemap.xml")
        text = resp.text
        assert "https://assay.tools/" in text
        assert "https://assay.tools/packages" in text
        assert "https://assay.tools/categories" in text
        assert "https://assay.tools/about" in text

    def test_sitemap_contains_category_pages(self, client, make_category):
        make_category(slug="ai-ml", name="AI & ML")
        resp = client.get("/sitemap.xml")
        assert "https://assay.tools/categories/ai-ml" in resp.text

    def test_sitemap_contains_evaluated_packages(self, client, make_package):
        make_package(id="stripe", name="Stripe", af_score=85.0)
        resp = client.get("/sitemap.xml")
        assert "https://assay.tools/packages/stripe" in resp.text

    def test_sitemap_excludes_unevaluated_packages(self, client, make_package):
        make_package(id="uneval", name="Unevaluated", af_score=None)
        resp = client.get("/sitemap.xml")
        assert "packages/uneval" not in resp.text


class TestMetaTags:
    def test_homepage_has_meta_description(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert '<meta name="description"' in resp.text

    def test_homepage_has_og_tags(self, client):
        resp = client.get("/")
        assert 'property="og:title"' in resp.text
        assert 'property="og:description"' in resp.text
        assert 'property="og:url"' in resp.text

    def test_homepage_has_canonical(self, client):
        resp = client.get("/")
        assert 'rel="canonical"' in resp.text

    def test_package_detail_has_jsonld(self, client, make_package):
        make_package(id="stripe", name="Stripe", af_score=85.0)
        resp = client.get("/packages/stripe")
        assert "application/ld+json" in resp.text
        assert '"SoftwareApplication"' in resp.text
