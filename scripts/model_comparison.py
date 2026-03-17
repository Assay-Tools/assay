"""Model comparison script for Assay evaluation quality testing.

Runs 10 packages through 4 models and compares AF, Security, and Reliability
scores against each other (does NOT write to DB).

Models tested:
  - claude-haiku-4-5-20251001  (current production)
  - claude-sonnet-4-6           (quality ceiling)
  - gemini-3-flash-preview      (Google cheap tier)
  - gpt-4o-mini                 (OpenAI cheap tier)

Usage:
    .venv/bin/python3 scripts/model_comparison.py
    .venv/bin/python3 scripts/model_comparison.py --output results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

# Add src/ to path so assay package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from assay.evaluation.evaluator import (
    SYSTEM_PROMPT,
    PackageEvaluation,
    build_user_prompt,
    compute_af_score,
    compute_reliability_score,
    compute_security_score,
    fetch_github_metadata,
    fetch_github_readme,
    fetch_package_manifest,
    parse_github_owner_repo,
)
from assay.database import SessionLocal
from assay.models.package import Package

# ---------------------------------------------------------------------------
# Package IDs to test — diverse across categories
# ---------------------------------------------------------------------------

PACKAGE_IDS = [
    "gotohuman-mcp-server",
    "claude-api",
    "docker-mcp-server",
    "resend-mcp",
    "server-wp-mcp",
    "fr24api-mcp",
    "mcp-server-sqlite",
    "mcp-server-everything",
    "mcp-server-filesystem",
    "alpha-vantage-mcp",
]

# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

MODELS = [
    {
        "id": "claude-haiku-4-5-20251001",
        "label": "Haiku 4.5",
        "provider": "anthropic",
    },
    {
        "id": "claude-sonnet-4-6",
        "label": "Sonnet 4.6",
        "provider": "anthropic",
    },
    {
        "id": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash",
        "provider": "gemini",
    },
    {
        "id": "gpt-4o-mini",
        "label": "GPT-4o mini",
        "provider": "openai",
    },
]

# Pricing per 1M tokens (input, output) — for cost estimation
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "gemini-3-flash-preview": (0.50, 3.00),
    "gpt-4o-mini": (0.15, 0.60),
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    package_id: str
    package_name: str
    model_id: str
    model_label: str
    af_score: float | None = None
    security_score: float | None = None
    reliability_score: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    duration_s: float = 0.0


# ---------------------------------------------------------------------------
# LLM callers — one per provider
# ---------------------------------------------------------------------------

def _parse_eval(raw_text: str) -> PackageEvaluation:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    json_text = raw_text.strip()
    if json_text.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*", "", json_text)
        json_text = re.sub(r"\s*```$", "", json_text)
    # Some models wrap in outer object — try direct parse first
    parsed = json.loads(json_text)
    return PackageEvaluation.model_validate(parsed)


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    in_price, out_price = MODEL_PRICING.get(model_id, (0, 0))
    return round(
        (input_tokens * in_price / 1_000_000) + (output_tokens * out_price / 1_000_000),
        6,
    )


def call_anthropic(model_id: str, package_name: str, context: dict) -> tuple[PackageEvaluation, dict]:
    from anthropic import Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(
        package_name, context["readme"], context["metadata"], context["manifest"]
    )
    response = client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return _parse_eval(raw), usage


def call_gemini(model_id: str, package_name: str, context: dict) -> tuple[PackageEvaluation, dict]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    user_prompt = build_user_prompt(
        package_name, context["readme"], context["metadata"], context["manifest"]
    )
    # Combine system prompt + user prompt (Gemini REST v1beta)
    combined_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": combined_prompt}]}],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.0},
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    usage_meta = data.get("usageMetadata", {})
    usage = {
        "input_tokens": usage_meta.get("promptTokenCount", 0),
        "output_tokens": usage_meta.get("candidatesTokenCount", 0),
    }
    return _parse_eval(raw), usage


def call_openai(model_id: str, package_name: str, context: dict) -> tuple[PackageEvaluation, dict]:
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)
    user_prompt = build_user_prompt(
        package_name, context["readme"], context["metadata"], context["manifest"]
    )
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    raw = response.choices[0].message.content
    usage = {
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
    }
    return _parse_eval(raw), usage


CALLERS = {
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "openai": call_openai,
}


# ---------------------------------------------------------------------------
# Context gathering (reuses evaluator logic)
# ---------------------------------------------------------------------------

def gather_context(package: Package) -> dict:
    context = {"readme": None, "metadata": None, "manifest": None}
    if not package.repo_url:
        return context
    parsed = parse_github_owner_repo(package.repo_url)
    if not parsed:
        return context
    owner, repo = parsed
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        context["metadata"] = fetch_github_metadata(owner, repo, http)
        context["readme"] = fetch_github_readme(owner, repo, http)
        branch = "main"
        if context["metadata"] and context["metadata"].get("default_branch"):
            branch = context["metadata"]["default_branch"]
        context["manifest"] = fetch_package_manifest(owner, repo, branch, http)
    return context


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_comparison(output_csv: str | None = None) -> list[EvalResult]:
    db = SessionLocal()
    packages = []
    for pkg_id in PACKAGE_IDS:
        pkg = db.get(Package, pkg_id)
        if pkg:
            packages.append(pkg)
        else:
            print(f"  WARNING: package '{pkg_id}' not found in DB, skipping")
    db.close()

    print(f"\nRunning comparison: {len(packages)} packages × {len(MODELS)} models")
    print(f"{'='*60}\n")

    results: list[EvalResult] = []

    for pkg in packages:
        print(f"Package: {pkg.name} ({pkg.id})")
        print(f"  Fetching GitHub context...")
        context = gather_context(pkg)
        has_readme = bool(context["readme"])
        has_meta = bool(context["metadata"])
        print(f"  Context: readme={'yes' if has_readme else 'no'}, meta={'yes' if has_meta else 'no'}")

        for model in MODELS:
            result = EvalResult(
                package_id=pkg.id,
                package_name=pkg.name,
                model_id=model["id"],
                model_label=model["label"],
            )
            caller = CALLERS[model["provider"]]
            print(f"  [{model['label']}] calling...", end=" ", flush=True)
            t0 = time.time()
            try:
                evaluation, usage = caller(model["id"], pkg.name, context)
                result.af_score = compute_af_score(evaluation.af_score_components)
                result.security_score = compute_security_score(evaluation.security_score_components)
                result.reliability_score = compute_reliability_score(evaluation.reliability_score_components)
                result.input_tokens = usage["input_tokens"]
                result.output_tokens = usage["output_tokens"]
                result.cost_usd = _estimate_cost(
                    model["id"], usage["input_tokens"], usage["output_tokens"]
                )
                result.duration_s = round(time.time() - t0, 1)
                print(f"AF={result.af_score:.1f} Sec={result.security_score:.1f} Rel={result.reliability_score:.1f} ({result.duration_s}s ${result.cost_usd:.4f})")
            except Exception as e:
                result.error = str(e)
                result.duration_s = round(time.time() - t0, 1)
                print(f"ERROR: {e}")
            results.append(result)
            time.sleep(0.5)  # be gentle to APIs

        print()

    # -- Summary table --
    print_summary(packages, results)

    # -- CSV export --
    if output_csv:
        write_csv(results, output_csv)
        print(f"\nResults written to {output_csv}")

    return results


def print_summary(packages, results: list[EvalResult]):
    model_labels = [m["label"] for m in MODELS]
    header = f"{'Package':<30} {'Metric':<12}" + "".join(f"{lbl:>14}" for lbl in model_labels)
    print("=" * len(header))
    print(header)
    print("=" * len(header))

    for pkg in packages:
        pkg_results = {r.model_label: r for r in results if r.package_id == pkg.id}
        for metric in ("AF", "Security", "Reliability"):
            row = f"{pkg.name[:29]:<30} {metric:<12}"
            for lbl in model_labels:
                r = pkg_results.get(lbl)
                if r and r.error is None:
                    val = {
                        "AF": r.af_score,
                        "Security": r.security_score,
                        "Reliability": r.reliability_score,
                    }[metric]
                    row += f"{val:>14.1f}"
                else:
                    row += f"{'ERR':>14}"
            print(row)
        print()

    # Cost summary
    print("\n--- Cost Summary ---")
    for model in MODELS:
        lbl = model["label"]
        model_results = [r for r in results if r.model_label == lbl and not r.error]
        total_cost = sum(r.cost_usd for r in model_results)
        total_in = sum(r.input_tokens for r in model_results)
        total_out = sum(r.output_tokens for r in model_results)
        avg_duration = sum(r.duration_s for r in model_results) / len(model_results) if model_results else 0
        print(f"  {lbl:<16} total=${total_cost:.4f}  in={total_in:,}  out={total_out:,}  avg_latency={avg_duration:.1f}s")


def write_csv(results: list[EvalResult], path: str):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "package_id", "package_name", "model_id", "model_label",
            "af_score", "security_score", "reliability_score",
            "input_tokens", "output_tokens", "cost_usd", "duration_s", "error",
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "package_id": r.package_id,
                "package_name": r.package_name,
                "model_id": r.model_id,
                "model_label": r.model_label,
                "af_score": r.af_score,
                "security_score": r.security_score,
                "reliability_score": r.reliability_score,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.cost_usd,
                "duration_s": r.duration_s,
                "error": r.error,
            })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assay model comparison experiment")
    parser.add_argument("--output", "-o", type=str, help="Write results to CSV file")
    args = parser.parse_args()

    # Load .secrets (excluding GCS_SA_KEY which has newlines)
    secrets_path = os.path.join(os.path.dirname(__file__), "..", ".secrets")
    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line and not line.startswith("GCS_SA_KEY"):
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    # Inject Gemini key
    os.environ.setdefault("GEMINI_API_KEY", "AIzaSyBuvokvlk4obRJ1_9vrm0JMV_vm1BsYE2k")

    run_comparison(output_csv=args.output)
