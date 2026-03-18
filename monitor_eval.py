#!/usr/bin/env python3
"""Monitor evaluation progress and log it every 60 seconds."""

import sqlite3
import time
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path

def get_status_counts():
    """Get counts of packages by status."""
    try:
        conn = sqlite3.connect('assay.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered,
                SUM(CASE WHEN af_score IS NOT NULL THEN 1 ELSE 0 END) as evaluated
            FROM packages
        """)
        result = cursor.fetchone()
        conn.close()
        return {
            'total': result[0],
            'discovered': result[1] or 0,
            'evaluated': result[2] or 0,
        }
    except Exception as e:
        return None

def is_runner_running():
    """Check if conservative_eval_runner.py is still running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "conservative_eval_runner"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("=" * 80)
    print("EVALUATION MONITOR - Starting")
    print("=" * 80)

    start_time = datetime.now()
    last_counts = None
    poll_interval = 60  # Check every 60 seconds

    def signal_handler(sig, frame):
        print("\n" + "=" * 80)
        print("Monitor stopped by user")
        print("=" * 80)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        counts = get_status_counts()

        if counts:
            pct = (counts['evaluated'] / counts['total'] * 100) if counts['total'] > 0 else 0
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            rate = (counts['evaluated'] - (last_counts['evaluated'] if last_counts else 0)) / (poll_interval/60) if last_counts else 0

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Evaluated: {counts['evaluated']:5d}/{counts['total']:5d} ({pct:5.1f}%) | "
                  f"Remaining: {counts['discovered']:5d} | "
                  f"Rate: {rate:5.1f} pkg/hr | "
                  f"ETA: {(counts['discovered']/(max(rate, 0.1))/60):.1f}h")

            last_counts = counts
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error reading database")

        if not is_runner_running():
            print("\n⚠ Runner process is not running! Check logs.")
            break

        time.sleep(poll_interval)

if __name__ == '__main__':
    main()
