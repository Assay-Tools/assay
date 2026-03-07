# Strategic Evaluation Session

YOUR TASK: Run strategic evaluations using the scheduler.

## How It Works

The batch evaluator uses the scheduler which processes packages in priority order:

1. **Flagged** — Packages explicitly flagged for re-evaluation (admin request, broken sub-components)
2. **Unevaluated** — Never-evaluated packages (high-priority and high-star first)
3. **Stale** — Packages not evaluated in 30+ days (oldest first)

## Commands

```bash
# Run strategic batch evaluation (recommended)
uv run python -m assay.evaluation.evaluator --batch --limit 500

# Check queue status first
curl -s https://assay.tools/v1/queue?limit=10 | python -m json.tool

# Check freshness stats
curl -s https://assay.tools/v1/stats | python -m json.tool

# Override: evaluate only high-priority packages
uv run python -m assay.evaluation.evaluator --batch --limit 100 --priority high

# Override: evaluate only MCP servers
uv run python -m assay.evaluation.evaluator --batch --limit 100 --package-type mcp_server

# Legacy: evaluate by raw status (bypasses scheduler)
uv run python -m assay.evaluation.evaluator --batch --status discovered --limit 50
```

## Expected Output

```
Scheduler queue: 500 packages (flagged: 3, unevaluated: 247, stale: 250)
Batch complete: 480/500 succeeded
By tier:
  flagged: 3 ok, 0 failed
  unevaluated: 235 ok, 12 failed
  stale: 242 ok, 8 failed
```

## Admin: Flag Packages for Re-evaluation

```bash
# Flag specific packages
curl -X POST https://assay.tools/admin/reevaluate \
  -H "X-Api-Key: $ASSAY_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"package_ids": ["stripe", "resend"]}'

# Bulk-flag all stale packages
curl -X POST https://assay.tools/admin/reevaluate \
  -H "X-Api-Key: $ASSAY_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filter": "stale"}'
```

## Goal

Maintain 30-day freshness across all evaluated packages. Check `evaluation_freshness_pct` in `/v1/stats` — target is 100%.
