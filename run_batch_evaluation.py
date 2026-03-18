#!/usr/bin/env python
"""
Continuous batch evaluation runner.
Runs batches of 20 packages with monitoring and progress tracking.
"""

import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_evaluation.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def run_batch(batch_num: int, limit: int = 20) -> bool:
    """Run a single batch of package evaluations."""
    logger.info(f"Starting batch {batch_num} (up to {limit} packages)")

    start_time = time.time()
    try:
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'assay.evaluation.evaluator',
                '--batch',
                f'--limit={limit}',
                '-v'
            ],
            cwd=Path('/Users/aj/git/assay'),
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout per batch
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            logger.info(f"Batch {batch_num} completed successfully in {elapsed:.1f}s")
            if result.stdout:
                logger.debug(f"Stdout:\n{result.stdout[-500:]}")  # Last 500 chars
            return True
        else:
            logger.error(f"Batch {batch_num} failed with return code {result.returncode}")
            logger.error(f"Stderr:\n{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Batch {batch_num} timed out after 1 hour")
        return False
    except Exception as e:
        logger.error(f"Batch {batch_num} raised exception: {e}")
        return False


def main():
    """Run continuous batch evaluation."""
    logger.info("Starting continuous batch evaluation")
    logger.info("Target: Evaluate all remaining unevaluated packages")
    logger.info("Batch size: 20 packages per batch")

    batch_num = 1
    successful_batches = 0
    failed_batches = 0

    # Run batches indefinitely until packages are exhausted
    # (The evaluator will return 0 packages when queue is empty)
    while True:
        success = run_batch(batch_num, limit=20)

        if success:
            successful_batches += 1
        else:
            failed_batches += 1
            # Continue on failure - evaluator may have hit rate limit
            logger.info("Waiting 30 seconds before retry...")
            time.sleep(30)

        batch_num += 1

        # After each batch, wait 5 seconds as specified
        logger.info("Waiting 5 seconds before next batch...")
        time.sleep(5)

        # Log progress every 10 batches
        if batch_num % 10 == 0:
            logger.info(
                f"Progress: {batch_num} batches attempted, "
                f"{successful_batches} successful, {failed_batches} failed"
            )


if __name__ == '__main__':
    main()
