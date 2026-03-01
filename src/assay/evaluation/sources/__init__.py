"""Discovery sources for the Assay pipeline."""

from .base import DiscoveredPackage, DiscoverySource
from .github import GitHubSource
from .mcp_registry import MCPRegistrySource
from .skills import GitHubAwesomeListSource, OpenClawSource

__all__ = [
    "DiscoveredPackage",
    "DiscoverySource",
    "GitHubSource",
    "MCPRegistrySource",
    "GitHubAwesomeListSource",
    "OpenClawSource",
]
