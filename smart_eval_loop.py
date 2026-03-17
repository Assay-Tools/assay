#!/usr/bin/env python3
"""Smart evaluation loop with rate-limit handling."""
import subprocess
import sqlite3
import time
import sys
from datetime import datetime

def get_remaining_count():
    """Get count of packages with 'discovered' status."""
    conn = sqlite3.connect('assay.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM packages WHERE status = "discovered"')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def run_batch(limit=10, batch_num=1):
    """Run a single evaluation batch with rate-limit handling."""
    cmd = [
        '.venv/bin/python',
        '-m', 'assay.evaluation.evaluator',
        '--batch',
        '--status', 'discovered',
        '--limit', str(limit)
    ]
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  [Attempt {attempt+1}/{max_retries}] ", end="", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            # Check output for rate limit indication
            if "rate_limit" in result.stderr.lower() or "429" in result.stderr:
                if attempt < max_retries - 1:
                    wait_time = 60 * (2 ** attempt)  # exponential backoff
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print("Rate limit hit, all retries exhausted")
                    return False, 0
            
            if result.returncode != 0 and "rate_limit" not in result.stderr.lower():
                print(f"Error (exit {result.returncode})")
                # Some errors are transient, keep trying
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                return False, 0
            
            # Success
            print("OK")
            # Count how many packages were removed
            return True, 0  # We'll check DB state instead
            
        except subprocess.TimeoutExpired:
            print("Timeout")
            if attempt < max_retries - 1:
                time.sleep(30)
                continue
            return False, 0
        except Exception as e:
            print(f"Exception: {e}")
            return False, 0
    
    return False, 0

def main():
    """Run evaluation batches with smart rate-limit handling."""
    batch_num = 0
    total_processed = 0
    start_time = datetime.now()
    
    print(f"Starting smart evaluation at {start_time.strftime('%H:%M:%S')}")
    print(f"Initial batch size: 10 packages (conservative to avoid rate limits)\n")
    
    while True:
        batch_num += 1
        before = get_remaining_count()
        
        if before == 0:
            print(f"\n✓ EVALUATION COMPLETE!")
            print(f"  Total batches: {batch_num - 1}")
            elapsed = datetime.now() - start_time
            print(f"  Time elapsed: {elapsed.total_seconds():.0f}s")
            sys.exit(0)
        
        # Reduce batch size if under 100 remaining to be conservative
        batch_size = 5 if before < 100 else 10
        
        print(f"[Batch {batch_num:4d}] Remaining: {before:5d} → ", end="", flush=True)
        
        success, processed = run_batch(limit=batch_size, batch_num=batch_num)
        
        after = get_remaining_count()
        batch_processed = before - after
        total_processed += batch_processed
        
        if batch_processed > 0:
            print(f"Processed {batch_processed} packages")
        else:
            if not success:
                print("Batch failed (no packages processed)")
                print("Waiting 60 seconds before retry...")
                time.sleep(60)
            else:
                print("Processed 0 packages (DB unchanged)")
        
        # Small delay between batches
        if before > 50:
            time.sleep(1)

if __name__ == '__main__':
    main()
