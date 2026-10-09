from __future__ import annotations
from db_repository import init_db, upsert_source, purge_demo_findings, list_sources


def seed_official_sources():
    """Seed only primary-source portals that are intentionally known and reviewable.

    These are source registry entries, not fabricated legislative findings. Findings are
    populated from live retrieval/search at runtime.
    """
    init_db()
    purge_demo_findings()
    sources = [
        {
            "id": "EU-EURLEX-RECENT",
            "jurisdiction": "European Union",
            "authority": "European Union",
            "name": "EUR-Lex — recent legal acts",
            "url": "https://eur-lex.europa.eu/collection/eu-law/legal-acts/recent.html",
            "source_type": "Official EU legislation portal",
            "language": "Multilingual",
            "verification_status": "verified official source",
            "retrieval_method": "HTML + web search",
            "active": True,
            "last_success": None,
            "last_failure": None,
            "error_state": None,
            "last_checked": None,
            "discovered_automatically": False,
            "discovery_reason": "Configured primary EU legal source.",
        },
        {
            "id": "NL-OFFICIAL-PUBLICATIONS",
            "jurisdiction": "Netherlands",
            "authority": "Government of the Netherlands",
            "name": "Netherlands Official Publications",
            "url": "https://www.officielebekendmakingen.nl/",
            "source_type": "Official publications portal",
            "language": "Dutch",
            "verification_status": "verified official source",
            "retrieval_method": "HTML + web search",
            "active": True,
            "last_success": None,
            "last_failure": None,
            "error_state": None,
            "last_checked": None,
            "discovered_automatically": False,
            "discovery_reason": "Configured Dutch official-publications source.",
        },
        {
            "id": "NL-WETTEN",
            "jurisdiction": "Netherlands",
            "authority": "Government of the Netherlands",
            "name": "Netherlands Legislation Database",
            "url": "https://wetten.overheid.nl/",
            "source_type": "Official legislation database",
            "language": "Dutch",
            "verification_status": "verified official source",
            "retrieval_method": "HTML + web search",
            "active": True,
            "last_success": None,
            "last_failure": None,
            "error_state": None,
            "last_checked": None,
            "discovered_automatically": False,
            "discovery_reason": "Configured Dutch legislation source.",
        },
    ]
    existing = set(list_sources()["id"].tolist()) if not list_sources().empty else set()
    for source in sources:
        if source["id"] not in existing:
            upsert_source(source)
