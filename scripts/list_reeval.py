"""List packages needing re-evaluation (old schema: tls_enforcement IS NULL)."""
import sys
sys.path.insert(0, "src")

from assay.database import SessionLocal, init_db
from assay.models.package import Package, PackageAgentReadiness

init_db()
db = SessionLocal()

results = (
    db.query(Package.id, Package.name, Package.repo_url, Package.homepage, Package.category_slug)
    .join(PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True)
    .filter(Package.status == "evaluated")
    .filter(Package.id != "stripe-api")
    .filter(
        (PackageAgentReadiness.tls_enforcement == None) |
        (PackageAgentReadiness.package_id == None)
    )
    .order_by(Package.id)
    .all()
)

print(f"Packages needing re-evaluation: {len(results)}")
for r in results:
    print(f"{r.id}\t{r.name}\t{r.repo_url or r.homepage or 'no-url'}")
db.close()
