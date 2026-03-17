#!/usr/bin/env python
"""
Continuous evaluation runner — processes batches of 20 packages repeatedly
until all packages are evaluated.

Usage:
    source .venv/bin/activate
    python scripts/continuous_eval.py [--limit 20] [--verbose]
"""

import subprocess
import sys
import time
from pathlib import Path

def run_batch(limit: int = 20, verbose: bool = False) -> dict:
    """Run one batch of evaluations."""
    cmd = [
        sys.executable,
        "-m",
        "assay.evaluation.evaluator",
        "--batch",
        f"--limit",
        str(limit),
    ]
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Continuous evaluation runner")
    parser.add_argument("--limit", type=int, default=20, help="Batch size")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    batch_num = 0
    total_success = 0
    total_failed = 0

    print("Starting continuous evaluation runner...")
    print(f"Batch size: {args.limit}")
    print()

    while True:
        batch_num += 1
        print(f"=== Batch {batch_num} ===")

        result = run_batch(limit=args.limit, verbose=args.verbose)

        # Parse output for results
        output = result.stdout + result.stderr
        print(output)

        # Check for "no more packages" message
        if "no more packages" in output.lower() or result.returncode != 0:
            print()
            print("Evaluation complete or error encountered.")
            print(f"Total batches processed: {batch_num}")
            break

        # Small delay between batches
        time.sleep(1)

    print()
    print("Evaluation run finished.")

if __name__ == "__main__":
    main()
