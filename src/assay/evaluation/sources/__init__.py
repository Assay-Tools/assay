"""Discovery sources for the Assay pipeline."""

from .base import DiscoveredPackage, DiscoverySource
from .github import GitHubSource
from .mcp_registry import MCPRegistrySource
from .npm import NpmSource
from .pypi import PyPISource
from .skills import GitHubAwesomeListSource, OpenClawSource
from .smithery import SmitherySource

__all__ = [
    "DiscoveredPackage",
    "DiscoverySource",
    "GitHubSource",
    "MCPRegistrySource",
    "GitHubAwesomeListSource",
    "OpenClawSource",
    "NpmSource",
    "PyPISource",
    "SmitherySource",
]
