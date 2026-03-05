"""API usage tracking — shared counters for analytics."""

from collections import defaultdict

# In-memory counters (per-process, reset on restart).
# Sufficient for single-process Railway deployment.
api_call_counts: dict[str, int] = defaultdict(int)
api_error_counts: dict[str, int] = defaultdict(int)
