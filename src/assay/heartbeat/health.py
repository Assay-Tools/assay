"""Site health checks — uptime, response time, SSL expiry."""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx


@dataclass
class HealthAlert:
    level: str  # "critical", "warning", "info"
    check: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def check_site_health(
    base_url: str = "https://assay.tools",
    timeout: float = 10.0,
    slow_threshold: float = 2.0,
) -> list[HealthAlert]:
    """Run site health checks and return any alerts."""
    alerts: list[HealthAlert] = []

    # Check main health endpoint
    try:
        resp = httpx.get(f"{base_url}/health", timeout=timeout)
        elapsed = resp.elapsed.total_seconds()

        if resp.status_code != 200:
            alerts.append(HealthAlert(
                level="critical",
                check="health_endpoint",
                message=f"Health endpoint returned {resp.status_code}",
            ))
        elif elapsed > slow_threshold:
            alerts.append(HealthAlert(
                level="warning",
                check="response_time",
                message=f"Health endpoint slow: {elapsed:.1f}s (threshold: {slow_threshold}s)",
            ))
    except httpx.RequestError as exc:
        alerts.append(HealthAlert(
            level="critical",
            check="site_reachable",
            message=f"Site unreachable: {exc}",
        ))
        return alerts  # No point checking more if site is down

    # Check key pages return 200
    key_pages = ["/", "/packages", "/categories", "/v1/stats"]
    for page in key_pages:
        try:
            resp = httpx.get(f"{base_url}{page}", timeout=timeout)
            if resp.status_code != 200:
                alerts.append(HealthAlert(
                    level="warning",
                    check="page_status",
                    message=f"{page} returned {resp.status_code}",
                ))
        except httpx.RequestError:
            alerts.append(HealthAlert(
                level="warning",
                check="page_status",
                message=f"{page} unreachable",
            ))

    # Check SSL certificate expiry
    hostname = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                not_after = datetime.strptime(
                    cert["notAfter"], "%b %d %H:%M:%S %Y %Z",
                ).replace(tzinfo=timezone.utc)
                days_left = (not_after - datetime.now(timezone.utc)).days

                if days_left <= 7:
                    alerts.append(HealthAlert(
                        level="critical",
                        check="ssl_expiry",
                        message=f"SSL cert expires in {days_left} days",
                    ))
                elif days_left <= 30:
                    alerts.append(HealthAlert(
                        level="warning",
                        check="ssl_expiry",
                        message=f"SSL cert expires in {days_left} days",
                    ))
    except Exception as exc:
        alerts.append(HealthAlert(
            level="warning",
            check="ssl_check",
            message=f"Could not check SSL: {exc}",
        ))

    return alerts
