# Deployment

This package is intentionally flat: all files live at repository root.

## Recommended deployment

Use Streamlit Community Cloud with the repository hosted on GitHub.

- Main file: `app.py`
- Python: 3.11 or 3.12
- `GITHUB_TOKEN`: only when Copilot analysis is desired
- `TAVILY_API_KEY`: optional but recommended for stable production web search
- `AUTO_WEB_DISCOVERY=true`: keeps autonomous web monitoring enabled

The app automatically checks whether the last live monitoring run is older than `AUTO_WEB_DISCOVERY_INTERVAL_MINUTES`. If it is due, it searches registered official sources and discovers additional source candidates during application startup.

## Why not GitHub Pages?

GitHub Pages serves static files and cannot run Python, SQLite/PostgreSQL access, report generation, web retrieval or the Copilot SDK. Keep the source in GitHub and use a Python-capable runtime such as Streamlit Community Cloud.

## Persistent production storage

A local SQLite database may be ephemeral on hosted runtimes. For production, use persistent PostgreSQL or another managed database while retaining the same repository interface.

## Scheduled monitoring

For stronger monitoring guarantees, run `services_web_discovery.run_live_monitoring(force=True)` from an external scheduler or GitHub Action connected to persistent storage. The app itself already performs due monitoring on startup/session access.

## Weekly schedule

The supplied `weekly-scan.yml` is scheduled for **Sunday 23:15 UTC**, so a normal scheduled run covers the completed Monday–Sunday reporting week. Manual runs use Monday through the current run date. Keep `TAVILY_API_KEY` as a GitHub Actions secret. The application preserves older database records for audit/history, but the live UI and exports show only the current reporting week.
