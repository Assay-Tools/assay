"""Pull existing evaluation context for a batch of packages.

Usage: uv run python scripts/batch_context.py --offset 0 --limit 10
"""
import json
import sys
import argparse
sys.path.insert(0, "src")

from assay.database import SessionLocal, init_db
from assay.models.package import Package, PackageAgentReadiness, PackageAuth, PackageInterface, PackagePricing, PackageRequirements

init_db()

parser = argparse.ArgumentParser()
parser.add_argument("--offset", type=int, default=0)
parser.add_argument("--limit", type=int, default=10)
args = parser.parse_args()

db = SessionLocal()

results = (
    db.query(Package)
    .join(PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True)
    .filter(Package.status == "evaluated")
    .filter(Package.id != "stripe-api")
    .filter(
        (PackageAgentReadiness.tls_enforcement == None) |
        (PackageAgentReadiness.package_id == None)
    )
    .order_by(Package.id)
    .offset(args.offset)
    .limit(args.limit)
    .all()
)

for pkg in results:
    ar = pkg.agent_readiness
    iface = pkg.interface
    auth = pkg.auth
    pricing = pkg.pricing
    req = pkg.requirements

    out = {
        "id": pkg.id,
        "name": pkg.name,
        "homepage": pkg.homepage,
        "repo_url": pkg.repo_url,
        "category_slug": pkg.category_slug,
        "what_it_does": pkg.what_it_does,
        "use_cases": json.loads(pkg.use_cases) if pkg.use_cases else [],
        "not_for": json.loads(pkg.not_for) if pkg.not_for else [],
        "best_when": pkg.best_when,
        "avoid_when": pkg.avoid_when,
        "alternatives": json.loads(pkg.alternatives) if pkg.alternatives else [],
        "tags": json.loads(pkg.tags) if pkg.tags else [],
        "version_evaluated": pkg.version_evaluated,
        "existing_af_score": pkg.af_score,
        "existing_security_score": pkg.security_score,
        "interface": {
            "has_rest_api": iface.has_rest_api if iface else None,
            "has_graphql": iface.has_graphql if iface else None,
            "has_grpc": iface.has_grpc if iface else None,
            "has_mcp_server": iface.has_mcp_server if iface else None,
            "mcp_server_url": iface.mcp_server_url if iface else None,
            "has_sdk": iface.has_sdk if iface else None,
            "sdk_languages": json.loads(iface.sdk_languages) if iface and iface.sdk_languages else [],
            "openapi_spec_url": iface.openapi_spec_url if iface else None,
            "webhooks": iface.webhooks if iface else None,
        } if iface else {},
        "auth": {
            "methods": json.loads(auth.methods) if auth and auth.methods else [],
            "oauth": auth.oauth if auth else None,
            "scopes": auth.scopes if auth else None,
            "notes": auth.notes if auth else None,
        } if auth else {},
        "pricing": {
            "model": pricing.model if pricing else None,
            "free_tier_exists": pricing.free_tier_exists if pricing else None,
        } if pricing else {},
        "requirements": {
            "requires_signup": req.requires_signup if req else None,
            "requires_credit_card": req.requires_credit_card if req else None,
            "compliance": json.loads(req.compliance) if req and req.compliance else [],
        } if req else {},
        "agent_readiness": {
            "mcp_server_quality": ar.mcp_server_quality if ar else None,
            "documentation_accuracy": ar.documentation_accuracy if ar else None,
            "error_message_quality": ar.error_message_quality if ar else None,
            "idempotency_support": ar.idempotency_support if ar else None,
            "pagination_style": ar.pagination_style if ar else None,
            "retry_guidance_documented": ar.retry_guidance_documented if ar else None,
            "known_agent_gotchas": json.loads(ar.known_agent_gotchas) if ar and ar.known_agent_gotchas else [],
            "old_security_score": ar.security_score if ar else None,
        } if ar else {},
    }
    print(json.dumps(out))

db.close()
