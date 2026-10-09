from __future__ import annotations
from db_repository import init_db
from db_seed import seed_official_sources
from services_web_discovery import run_live_monitoring

if __name__ == "__main__":
    init_db()
    seed_official_sources()
    result = run_live_monitoring(force=True)
    scope = result.get("jurisdiction_scan", {})
    ingestion = result.get("ingestion", {})
    total = int(scope.get("findings", 0) or 0) + int(ingestion.get("findings", 0) or 0)
    print(f"Weekly compliance scan complete: {scope.get('jurisdictions_checked', 0)} jurisdictions checked; {total} findings stored/updated.")
