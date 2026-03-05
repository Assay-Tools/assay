"""Tests for the Assay CLI."""

from unittest.mock import MagicMock, patch

import pytest

from assay.cli import cmd_check, cmd_compare, cmd_stale


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestCheck:
    def test_check_prints_scores(self, capsys):
        pkg = {
            "id": "stripe",
            "name": "Stripe",
            "what_it_does": "Payment processing",
            "af_score": 85.0,
            "security_score": 90.0,
            "reliability_score": 88.0,
            "category": {"name": "Payments"},
            "last_evaluated": "2026-03-01T00:00:00Z",
            "version_evaluated": "2024.1",
            "interface": {"has_rest_api": True, "has_mcp_server": False},
        }
        with patch("assay.cli._client") as mock_client:
            client = MagicMock()
            client.__enter__ = MagicMock(return_value=client)
            client.__exit__ = MagicMock(return_value=False)
            client.get.return_value = _mock_response(pkg)
            mock_client.return_value = client

            args = MagicMock(package="stripe", base_url="http://test", json=False)
            cmd_check(args)

        output = capsys.readouterr().out
        assert "Stripe" in output
        assert "85/100" in output
        assert "90/100" in output
        assert "88/100" in output

    def test_check_not_found(self):
        with patch("assay.cli._client") as mock_client:
            client = MagicMock()
            client.__enter__ = MagicMock(return_value=client)
            client.__exit__ = MagicMock(return_value=False)
            client.get.return_value = _mock_response({}, status_code=404)
            mock_client.return_value = client

            args = MagicMock(package="nonexistent", base_url="http://test", json=False)
            with pytest.raises(SystemExit):
                cmd_check(args)


class TestCompare:
    def test_compare_table(self, capsys):
        data = {
            "packages": [
                {"id": "a", "name": "Package A", "af_score": 90.0,
                 "security_score": 85.0, "reliability_score": 80.0},
                {"id": "b", "name": "Package B", "af_score": 70.0,
                 "security_score": 65.0, "reliability_score": 75.0},
            ]
        }
        with patch("assay.cli._client") as mock_client:
            client = MagicMock()
            client.__enter__ = MagicMock(return_value=client)
            client.__exit__ = MagicMock(return_value=False)
            client.get.return_value = _mock_response(data)
            mock_client.return_value = client

            args = MagicMock(
                packages=["a", "b"], base_url="http://test", json=False,
            )
            cmd_compare(args)

        output = capsys.readouterr().out
        assert "Package A" in output
        assert "Package B" in output
        assert "90" in output
        assert "70" in output


class TestStale:
    def test_stale_shows_queue(self, capsys):
        data = {
            "count": 2,
            "queue": [
                {"id": "old-pkg", "name": "Old", "status": "needs_reevaluation",
                 "reason": "stale", "last_evaluated": "2025-01-01T00:00:00Z",
                 "current_af_score": 60.0, "priority": None, "stars": None},
                {"id": "new-pkg", "name": "New", "status": "needs_evaluation",
                 "priority": "high", "stars": 500},
            ],
        }
        with patch("assay.cli._client") as mock_client:
            client = MagicMock()
            client.__enter__ = MagicMock(return_value=client)
            client.__exit__ = MagicMock(return_value=False)
            client.get.return_value = _mock_response(data)
            mock_client.return_value = client

            args = MagicMock(
                days=90, limit=50, base_url="http://test", json=False,
            )
            cmd_stale(args)

        output = capsys.readouterr().out
        assert "old-pkg" in output
        assert "new-pkg" in output
        assert "stale" in output
        assert "Total: 2" in output

    def test_stale_empty(self, capsys):
        data = {"count": 0, "queue": []}
        with patch("assay.cli._client") as mock_client:
            client = MagicMock()
            client.__enter__ = MagicMock(return_value=client)
            client.__exit__ = MagicMock(return_value=False)
            client.get.return_value = _mock_response(data)
            mock_client.return_value = client

            args = MagicMock(
                days=90, limit=50, base_url="http://test", json=False,
            )
            cmd_stale(args)

        output = capsys.readouterr().out
        assert "No packages" in output
