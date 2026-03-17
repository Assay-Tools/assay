#!/usr/bin/env python
"""
Continuous evaluation fleet runner.

Processes batches of 500 packages through the evaluator until all
remaining unevaluated packages are complete.

Usage:
    python run_evaluation_fleet.py [--batch-size 500]
"""

import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from assay.database import SessionLocal
from assay.models.package import Package
from sqlalchemy import func

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_stats():
    """Get current evaluation statistics."""
    db = SessionLocal()
    try:
        total = db.query(func.count(Package.id)).scalar() or 0
        evaluated = (
            db.query(func.count(Package.id))
            .filter(Package.af_score.isnot(None))
            .scalar() or 0
        )
        unevaluated = (
            db.query(func.count(Package.id))
            .filter(Package.af_score.is_(None))
            .scalar() or 0
        )
        return {
            "total": total,
            "evaluated": evaluated,
            "unevaluated": unevaluated,
            "percent_complete": (evaluated / total * 100) if total > 0 else 0,
        }
    finally:
        db.close()


def run_evaluation_batch(batch_num: int, batch_size: int = 500):
    """Run a single batch of evaluations."""
    logger.info(f"Starting batch {batch_num} with limit {batch_size}")

    cmd = [
        sys.executable,
        "-m",
        "assay.evaluation.evaluator",
        "--batch",
        "--limit",
        str(batch_size),
    ]

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running batch {batch_num}: {e}")
        return False


def main():
    """Run continuous evaluation batches until completion."""
    batch_size = 500
    batch_num = 1

    logger.info("=" * 70)
    logger.info("ASSAY EVALUATION FLEET - Continuous Package Evaluation")
    logger.info("=" * 70)

    initial_stats = get_stats()
    logger.info(
        f"Initial state: {initial_stats['evaluated']:,}/{initial_stats['total']:,} "
        f"evaluated ({initial_stats['percent_complete']:.1f}%)"
    )

    start_time = time.time()

    while True:
        stats = get_stats()

        if stats["unevaluated"] == 0:
            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info("EVALUATION COMPLETE!")
            logger.info(f"All {stats['total']:,} packages have been evaluated")
            logger.info(f"Total time: {elapsed/3600:.1f} hours")
            logger.info("=" * 70)
            break

        logger.info(
            f"[Batch {batch_num}] "
            f"{stats['evaluated']:,}/{stats['total']:,} evaluated "
            f"({stats['percent_complete']:.1f}%) - "
            f"{stats['unevaluated']:,} remaining"
        )

        success = run_evaluation_batch(batch_num, batch_size)

        if not success:
            logger.warning(f"Batch {batch_num} may have had issues, but continuing...")

        batch_num += 1

        # Give the system a moment between batches
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nEvaluation interrupted by user")
        sys.exit(1)
