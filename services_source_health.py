from __future__ import annotations
from datetime import datetime, timezone
import requests
from db_repository import list_sources, upsert_source


def check_all_sources(timeout: int = 20):
    df = list_sources()
    results = []
    for record in df.to_dict("records"):
        if not record.get("active"):
            continue
        checked = datetime.now(timezone.utc).isoformat()
        try:
            response = requests.get(
                record["url"], timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "ComplianceIntelligence/1.1"},
            )
            response.raise_for_status()
            record["last_success"] = checked
            record["error_state"] = None
            status = "healthy"
        except Exception as exc:
            record["last_failure"] = checked
            record["error_state"] = str(exc)[:300]
            status = "error"
        record["last_checked"] = checked
        upsert_source(record)
        results.append({"id": record["id"], "name": record["name"], "status": status, "checked": checked})
    return results


if __name__ == "__main__":
    from db_seed import seed_official_sources
    seed_official_sources()
    for result in check_all_sources():
        print(result)
