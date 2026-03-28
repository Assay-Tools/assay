"""Base class and data structures for discovery sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DiscoveredPackage:
    """Standardized package stub returned by all discovery sources."""

    id: str
    name: str
    repo_url: str | None = None
    homepage: str | None = None
    description: str | None = None
    topics: list[str] = field(default_factory=list)
    stars: int = 0
    last_active: str | None = None  # ISO date
    package_type: str = "mcp_server"  # mcp_server, skill
    discovery_source: str = "github"  # github, mcp_registry, github_awesome, openclaw, community


class DiscoverySource(ABC):
    """Abstract base class for discovery sources."""

    known_ids: set[str] = set()
    known_normalized_names: set[str] = set()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source (e.g. 'github', 'mcp_registry')."""

    @abstractmethod
    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Discover packages from this source. Returns up to `limit` results."""
