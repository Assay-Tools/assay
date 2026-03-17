#!/usr/bin/env python
"""Continuous package evaluation runner - processes batches until completion."""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Change to repo directory
REPO_DIR = Path(__file__).parent
sys.path.insert(0, str(REPO_DIR / "src"))

from assay.database import SessionLocal
from assay.models.package import Package

def count_unevaluated():
    """Count packages still needing evaluation."""
    db = SessionLocal()
    try:
        unevaluated = db.query(Package).filter(Package.af_score.is_(None)).count()
        total = db.query(Package).count()
        return unevaluated, total
    finally:
        db.close()

def run_batch(batch_size=20):
    """Run a single batch evaluation."""
    cmd = [
        sys.executable,
        "-m",
        "assay.evaluation.evaluator",
        "--batch",
        f"--limit",
        str(batch_size),
    ]

    try:
        result = subprocess.run(cmd, cwd=str(REPO_DIR), timeout=3600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Batch evaluation timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error running batch: {e}", file=sys.stderr)
        return False

def main():
    batch_size = 20
    batch_num = 0

    print(f"Starting continuous evaluation at {datetime.now().strftime('%H:%M:%S')}")
    print(f"Batch size: {batch_size} packages per batch")

    while True:
        batch_num += 1
        unevaluated, total = count_unevaluated()

        print(f"\n{'='*60}")
        print(f"Batch {batch_num} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"Status: {total - unevaluated}/{total} evaluated, {unevaluated} remaining")
        print(f"{'='*60}")

        if unevaluated == 0:
            print("✓ All packages evaluated!")
            break

        if unevaluated < batch_size:
            print(f"Final batch: {unevaluated} packages")

        # Run batch
        success = run_batch(batch_size=batch_size)

        # Check status again
        unevaluated_after, _ = count_unevaluated()
        batch_processed = unevaluated - unevaluated_after

        print(f"Batch result: {batch_processed} packages processed")

        if batch_processed == 0 and unevaluated > 0:
            print("WARNING: No progress made in batch. Waiting before retry...")
            time.sleep(10)
        else:
            # Brief pause between batches
            print("Pausing before next batch...")
            time.sleep(3)

if __name__ == "__main__":
    main()
