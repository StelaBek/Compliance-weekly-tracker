# Architecture

## Runtime flow

1. `app.py` initializes persistence and the verified source registry.
2. When live monitoring is due, `services_web_discovery.py` searches registered official domains, directly inspects source pages, and stores relevant source-backed findings.
3. The same service rotates through European jurisdictions to discover additional candidate official sources. Candidates are stored as `pending verification`; they are not used as authoritative findings until approved.
4. `db_repository.py` stores findings, source provenance, source status, runtime sync state and field-level edit history.
5. `core_analytics.py` calculates deterministic executive metrics and summary text from the current records.
6. `ai_copilot_service.py` receives structured evidence only when the user asks for AI interpretation.
7. `services_exports.py` builds PDF and PPTX outputs from the visible filtered result.

## Web-search strategy

- Tavily is preferred when `TAVILY_API_KEY` is configured.
- DDGS is the no-key fallback.
- Registered source pages are also crawled directly for relevant same-domain links.
- Search results outside the registered official domain are not silently ingested as authoritative findings.
- New source candidates use a conservative `pending verification` state.
- Missing dates, deadlines, legal status, applicability and obligations remain unknown unless supported by source material or a later human edit.

## Presentation architecture

The UI is intentionally separate from source retrieval and analysis logic. Theme-aware CSS uses Streamlit's light/dark variables while applying purple/yellow brand accents. This keeps a future frontend replacement possible without rewriting the regulatory pipeline.

## Flat packaging

All modules are root-level files because this distribution is designed for a flat GitHub upload. Prefixes and descriptive filenames replace folder grouping.

## Weekly recency and verification gate

The ingestion pipeline applies a hard reporting gate before persistence. A result is stored only when: (1) it is relevant to the configured compliance taxonomy, (2) its publication/update date falls inside the current ISO reporting week and is on/after 2026-01-01, (3) a legal reference is extractable from the official evidence, (4) the source is a registered official source or passes the official-domain verification rules, and (5) the evidence indicates a material event such as publication, amendment, adoption, official update, implementing/delegated act, guidance, enforcement development or compliance milestone. This intentionally favors precision over recall.
