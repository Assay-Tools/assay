"""Tests for stats and queue API endpoints."""


class TestStats:
    def test_stats_empty_db(self, client):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_packages"] == 0
        assert data["total_evaluated"] == 0
        assert data["total_categories"] == 0
        assert data["avg_af_score"] is None
        assert data["score_distribution"]["excellent"] == 0

    def test_stats_with_data(self, client, sample_packages):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_packages"] == 6
        assert data["total_evaluated"] == 5  # one has af_score=None
        assert data["total_categories"] == 2

    def test_score_distribution(self, client, sample_packages):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        dist = resp.json()["score_distribution"]

        # top-api: 92 (excellent), mid-tool: 68 (good), basic-sdk: 52 (fair),
        # legacy-api: 30 (poor), low-sdk: 35 (poor)
        assert dist["excellent"] == 1
        assert dist["good"] == 1
        assert dist["fair"] == 1
        assert dist["poor"] == 2
        assert dist["unrated"] == 1

    def test_avg_af_score(self, client, sample_packages):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        avg = resp.json()["avg_af_score"]
        # (92 + 68 + 52 + 30 + 35) / 5 = 55.4
        assert avg == 55.4


class TestQueue:
    def test_queue_returns_unevaluated(self, client, sample_packages):
        resp = client.get("/v1/queue")
        assert resp.status_code == 200
        data = resp.json()
        needs_eval = [q for q in data["queue"] if q["status"] == "needs_evaluation"]
        assert len(needs_eval) >= 1
        ids = {q["id"] for q in needs_eval}
        assert "new-pkg" in ids

    def test_queue_limit(self, client, sample_packages):
        resp = client.get("/v1/queue?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["queue"]) <= 1

    def test_queue_filter_by_type(self, client, sample_packages):
        resp = client.get("/v1/queue?package_type=mcp_server")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["queue"]:
            assert item["package_type"] == "mcp_server"
