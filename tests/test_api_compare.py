"""Tests for compare API endpoint."""


class TestCompare:
    def test_compare_two_packages(self, client, sample_packages):
        resp = client.get("/v1/compare?ids=top-api,mid-tool")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 2

    def test_compare_single_package(self, client, sample_packages):
        resp = client.get("/v1/compare?ids=top-api")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 1

    def test_compare_missing_package(self, client, sample_packages):
        resp = client.get("/v1/compare?ids=top-api,nonexistent")
        assert resp.status_code == 404
        assert "nonexistent" in resp.json()["detail"]

    def test_compare_empty_ids(self, client):
        resp = client.get("/v1/compare?ids=")
        assert resp.status_code == 400

    def test_compare_too_many(self, client, sample_packages):
        ids = ",".join(f"pkg-{i}" for i in range(11))
        resp = client.get(f"/v1/compare?ids={ids}")
        assert resp.status_code == 400
        assert "Maximum 10" in resp.json()["detail"]

    def test_compare_returns_full_data(self, client, sample_packages):
        resp = client.get("/v1/compare?ids=top-api")
        assert resp.status_code == 200
        pkg = resp.json()["packages"][0]
        assert "af_score" in pkg
        assert "security_score" in pkg
        assert "interface" in pkg
