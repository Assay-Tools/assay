#!/usr/bin/env python3
"""Run evaluation with intelligent backoff for OpenAI rate limits."""
import sqlite3
import time
import sys
from datetime import datetime
from src.assay.evaluation.evaluator import EvaluationAgent

def get_remaining_count():
    """Get count of packages with 'discovered' status."""
    conn = sqlite3.connect('assay.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM packages WHERE status = "discovered"')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def run_batch_with_backoff(agent, batch_size=5, batch_num=1, max_wait=300):
    """Run a batch with exponential backoff on rate limit."""
    wait_time = 1
    attempt = 0
    
    while wait_time <= max_wait:
        attempt += 1
        try:
            print(f"  [Attempt {attempt}] Processing {batch_size} packages...", flush=True, end="")
            results = agent.evaluate_batch(status='discovered', limit=batch_size)
            processed = results.get('success', 0)
            total = results.get('total', 0)
            print(f" ✓ {processed}/{total}")
            return processed, total > 0
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                print(f" Rate limited")
                print(f"    Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, max_wait)  # exponential backoff
            else:
                # Non-rate-limit error - could be validation, etc
                print(f" Error: {error_str[:100]}")
                return 0, total > 0
    
    print(f"  [TIMEOUT] Exceeded max backoff ({max_wait}s)")
    return 0, False

def main():
    """Main evaluation loop with smart backoff."""
    agent = EvaluationAgent()
    print("Evaluation Agent initialized\n")
    
    batch_num = 0
    total_processed = 0
    start_time = datetime.now()
    
    print(f"Starting evaluation at {start_time.strftime('%H:%M:%S')}")
    print(f"Batch size: 5 packages (conservative)\n")
    
    try:
        while True:
            batch_num += 1
            before = get_remaining_count()
            
            if before == 0:
                print(f"\n✓ EVALUATION COMPLETE!")
                print(f"  Total batches: {batch_num - 1}")
                print(f"  Total processed: {total_processed}")
                elapsed = datetime.now() - start_time
                mins = elapsed.total_seconds() / 60
                rate = total_processed / max(1, mins)
                print(f"  Time: {mins:.1f} minutes ({rate:.1f} pkg/min)")
                break
            
            print(f"[Batch {batch_num:4d}] Remaining: {before:5d} → ", end="", flush=True)
            
            processed, more_available = run_batch_with_backoff(agent, batch_size=5, batch_num=batch_num)
            
            total_processed += processed
            
            if processed == 0 and before > 0:
                print("  [No packages processed, but DB shows remaining]")
                if not more_available:
                    print("    Waiting 30s before retry...")
                    time.sleep(30)
            
            # Small delay between batches
            if before > 100:
                time.sleep(0.5)
    
    finally:
        agent.close()
        print("\nAgent closed")

if __name__ == '__main__':
    main()
