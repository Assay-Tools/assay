"""Discovery sources for the Assay pipeline."""

from .base import DiscoveredPackage, DiscoverySource
from .crates_io import CratesIoSource
from .cursor_directory import CursorDirectorySource
from .docker_mcp import DockerMCPSource
from .github import GitHubSource
from .glama import GlamaSource
from .mcp_registry import MCPRegistrySource
from .mcp_run import MCPRunSource
from .mcp_so import MCPSoSource
from .npm import NpmSource
from .pypi import PyPISource
from .skills import GitHubAwesomeListSource, OpenClawSource
from .smithery import SmitherySource

__all__ = [
    "CratesIoSource",
    "CursorDirectorySource",
    "DiscoveredPackage",
    "DiscoverySource",
    "DockerMCPSource",
    "GitHubAwesomeListSource",
    "GitHubSource",
    "GlamaSource",
    "MCPRegistrySource",
    "MCPRunSource",
    "MCPSoSource",
    "NpmSource",
    "OpenClawSource",
    "PyPISource",
    "SmitherySource",
]
