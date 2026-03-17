#!/usr/bin/env python
"""Continuous evaluation runner — processes packages in batches until none remain.

Usage:
    source .venv/bin/activate
    python run_continuous_evaluation.py [--batch-size 20] [--sleep 2]

This script repeatedly runs batches of package evaluations until the scheduler
reports "no more packages".
"""

import argparse
import logging
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_batch(batch_size: int) -> bool:
    """Run a single batch. Returns True if packages were evaluated, False if none remaining."""
    cmd = [
        sys.executable,
        "-m",
        "assay.evaluation.evaluator",
        "--batch",
        f"--limit={batch_size}",
    ]

    logger.info(f"Starting batch of {batch_size} packages...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Log output
    if result.stdout:
        logger.info("Batch output: %s", result.stdout.strip())

    if result.stderr and "ERROR" in result.stderr:
        logger.error("Batch failed: %s", result.stderr.strip())
        return False

    # Check if any packages were processed
    if "0/0 succeeded" in result.stdout or "Batch complete: 0/" in result.stdout:
        logger.info("No more packages to evaluate.")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Continuously evaluate packages in batches"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of packages per batch (default: 20)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2,
        help="Seconds to sleep between batches (default: 2)",
    )
    args = parser.parse_args()

    logger.info("Starting continuous evaluation (batch size: %d)", args.batch_size)
    logger.info("Press Ctrl+C to stop")

    batch_num = 0
    try:
        while True:
            batch_num += 1
            logger.info(f"\n--- Batch {batch_num} ---")

            if not run_batch(args.batch_size):
                logger.info("Evaluation complete!")
                break

            if args.sleep > 0:
                logger.info(f"Sleeping {args.sleep}s before next batch...")
                time.sleep(args.sleep)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
