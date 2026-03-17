#!/bin/bash

# Continuous evaluation runner
# Processes packages in batches until all are evaluated

source .venv/bin/activate

BATCH_SIZE=20
BATCH_NUM=0
TOTAL_PROCESSED=0

echo "Starting continuous evaluation"
echo "Batch size: $BATCH_SIZE packages"
echo ""

while true; do
    BATCH_NUM=$((BATCH_NUM + 1))

    # Get remaining count
    REMAINING=$(python3 -c "
import sqlite3
conn = sqlite3.connect('assay.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM packages WHERE af_score IS NULL')
count = cursor.fetchone()[0]
conn.close()
print(count)
")

    if [ "$REMAINING" -eq 0 ]; then
        echo ""
        echo "✓ EVALUATION COMPLETE!"
        echo "Total batches: $BATCH_NUM"
        echo "Total packages evaluated: $TOTAL_PROCESSED"
        break
    fi

    echo "[Batch $BATCH_NUM] Remaining: $REMAINING packages - Processing..."

    python -m assay.evaluation.evaluator --batch --limit $BATCH_SIZE 2>&1 | tail -5

    TOTAL_PROCESSED=$((TOTAL_PROCESSED + BATCH_SIZE))

    sleep 1
done

echo "Done!"
