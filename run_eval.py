#!/usr/bin/env python3
import subprocess
import sqlite3
import sys
import time
from datetime import datetime

def get_remaining_count():
    """Get count of packages with 'discovered' status."""
    conn = sqlite3.connect('assay.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM packages WHERE status = "discovered"')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def run_batch(limit=30):
    """Run a single evaluation batch."""
    cmd = [
        '.venv/bin/python',
        '-m', 'assay.evaluation.evaluator',
        '--batch',
        '--status', 'discovered',
        '--limit', str(limit)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Batch processing exceeded 5 minutes")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    batch_num = 0
    total_processed = 0
    start_time = datetime.now()
    
    print(f"Starting evaluation at {start_time.strftime('%H:%M:%S')}")
    print(f"Batch size: 30 packages per batch")
    print(f"Will continue until all packages evaluated\n")
    
    while True:
        batch_num += 1
        before = get_remaining_count()
        
        if before == 0:
            print(f"\n✓ EVALUATION COMPLETE!")
            print(f"  Total batches: {batch_num - 1}")
            print(f"  Total processed: {total_processed}")
            elapsed = datetime.now() - start_time
            print(f"  Time elapsed: {elapsed.total_seconds():.1f}s")
            break
        
        print(f"[Batch {batch_num:3d}] Remaining: {before:5d} packages ", end="", flush=True)
        
        # Run batch
        success = run_batch(limit=30)
        
        after = get_remaining_count()
        processed = before - after
        total_processed += processed
        
        if success:
            print(f"→ Processed {processed:2d} packages")
        else:
            print(f"→ Error or timeout")
        
        # Small delay to avoid hammering
        if before > 100:
            time.sleep(0.5)
        else:
            time.sleep(1)

if __name__ == '__main__':
    main()
