#!/bin/bash
# Start continuous batch evaluation until all packages are evaluated

cd /Users/aj/git/assay

BATCH_SIZE=20
BATCH_NUM=0

echo "Starting batch evaluation at $(date '+%Y-%m-%d %H:%M:%S')"
echo "Batch size: $BATCH_SIZE packages per batch"

while true; do
    BATCH_NUM=$((BATCH_NUM + 1))

    # Get current status
    STATUS=$(/Users/aj/git/assay/.venv/bin/python << 'PYEOF'
import sys
sys.path.insert(0, '/Users/aj/git/assay/src')
from assay.database import SessionLocal
from assay.models.package import Package
db = SessionLocal()
total = db.query(Package).count()
evaluated = db.query(Package).filter(Package.af_score.isnot(None)).count()
unevaluated = total - evaluated
db.close()
print(f"{total}|{evaluated}|{unevaluated}")
PYEOF
)

    IFS='|' read -r total evaluated unevaluated <<< "$STATUS"

    echo ""
    echo "========================================"
    echo "Batch $BATCH_NUM - $(date '+%H:%M:%S')"
    echo "Status: $evaluated/$total evaluated, $unevaluated remaining"
    echo "========================================"

    if [ "$unevaluated" == "0" ]; then
        echo "✓ All packages evaluated!"
        break
    fi

    # Run batch evaluation
    /Users/aj/git/assay/.venv/bin/python -m assay.evaluation.evaluator --batch --limit $BATCH_SIZE

    # Brief pause between batches
    sleep 2
done

echo ""
echo "Evaluation complete at $(date '+%Y-%m-%d %H:%M:%S')"
