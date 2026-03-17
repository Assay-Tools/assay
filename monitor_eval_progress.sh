#!/bin/bash
# Periodic evaluation progress monitor
# Run as: bash monitor_eval_progress.sh

source .venv/bin/activate

while true; do
    clear
    python << 'PYTHON'
import sys
sys.path.insert(0, 'src')

from assay.database import SessionLocal
from assay.models.package import Package
from sqlalchemy import func
from datetime import datetime

db = SessionLocal()

total = db.query(func.count(Package.id)).scalar() or 0
evaluated = db.query(func.count(Package.id)).filter(Package.af_score.isnot(None)).scalar() or 0
unevaluated = db.query(func.count(Package.id)).filter(Package.af_score.is_(None)).scalar() or 0
percent = evaluated/total*100 if total > 0 else 0

print(f"╔{'═'*58}╗")
print(f"║ ASSAY EVALUATION PROGRESS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<25} ║")
print(f"╠{'═'*58}╣")
print(f"║ Total packages:    {total:>10,}                              ║")
print(f"║ Evaluated:         {evaluated:>10,} ({percent:>5.1f}%)                      ║")
print(f"║ Remaining:         {unevaluated:>10,} ({100-percent:>5.1f}%)                      ║")
print(f"╠{'═'*58}╣")

# Simple progress bar
bar_width = 50
filled = int(bar_width * percent / 100)
bar = '█' * filled + '░' * (bar_width - filled)
print(f"║ Progress: [{bar}] ║")
print(f"╚{'═'*58}╝")

db.close()
PYTHON

    # Show last few log lines
    echo ""
    echo "Last batch status:"
    tail -3 fleet_runner.log 2>/dev/null | sed 's/^/  /'
    
    echo ""
    echo "Press Ctrl+C to stop monitoring. Updating every 30 seconds..."
    sleep 30
done
