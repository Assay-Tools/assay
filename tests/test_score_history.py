"""Tests for score history tracking."""

from assay.models import ScoreSnapshot


class TestScoreHistoryAPI:
    def test_empty_history(self, client, sample_packages):
        resp = client.get("/v1/packages/top-api/score-history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["package_id"] == "top-api"
        assert data["snapshots"] == []

    def test_history_with_snapshots(self, client, db, sample_packages):
        # Add some snapshots
        for i, score in enumerate([85.0, 88.0, 92.0]):
            snap = ScoreSnapshot(
                package_id="top-api",
                af_score=score,
                security_score=80.0 + i,
                reliability_score=75.0 + i,
            )
            db.add(snap)
        db.commit()

        resp = client.get("/v1/packages/top-api/score-history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["snapshots"]) == 3
        af_scores = {s["af_score"] for s in data["snapshots"]}
        assert af_scores == {85.0, 88.0, 92.0}

    def test_history_nonexistent_package(self, client):
        resp = client.get("/v1/packages/nonexistent/score-history")
        assert resp.status_code == 404

    def test_history_limit(self, client, db, sample_packages):
        for i in range(10):
            snap = ScoreSnapshot(
                package_id="top-api",
                af_score=float(50 + i),
            )
            db.add(snap)
        db.commit()

        resp = client.get("/v1/packages/top-api/score-history?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["snapshots"]) == 3


class TestScoreSnapshotModel:
    def test_create_snapshot(self, db, sample_packages):
        snap = ScoreSnapshot(
            package_id="top-api",
            af_score=92.0,
            security_score=90.0,
            reliability_score=88.0,
        )
        db.add(snap)
        db.commit()

        saved = db.query(ScoreSnapshot).first()
        assert saved.package_id == "top-api"
        assert saved.af_score == 92.0
        assert saved.recorded_at is not None
