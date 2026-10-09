# European Product & Tax Compliance Intelligence

A GitHub-friendly Streamlit application for European product and tax regulatory monitoring. The application continuously searches registered official sources, discovers new source candidates on the public web, stores source-backed findings, supports manual editing with change history, adds optional grounded GitHub Copilot analysis, and exports the current result to PDF and PowerPoint.

## What changed in this version

- No fictional/demo findings are seeded.
- Live web monitoring runs automatically when the application starts and is due for a refresh.
- The default refresh interval is 60 minutes and can be changed with an environment variable.
- Registered official sources are searched automatically, even if you never click a search button.
- New official-source candidates are discovered automatically and placed in **pending verification** rather than silently treated as authoritative.
- You can still add or update your own sources in the **Sources** page.
- A manual **Search the web now** button is available when you want to force an immediate refresh.
- The interface uses Streamlit theme variables so the custom design remains legible in both light and dark mode.
- PDF and PPTX export remain available from the Overview.

## How live web search works

The app uses two complementary methods:

1. **Registered-source monitoring** — it searches within registered official domains and directly inspects links found on those source pages. Relevant official-source pages are stored as live findings.
2. **Automatic source discovery** — it rotates through the European jurisdiction list and searches for likely official gazettes, legislation databases, tax authorities and regulatory bodies. Newly discovered sources are stored as `pending verification` until you approve them.

For public web search, the app prefers **Tavily** when `TAVILY_API_KEY` is configured. Without Tavily it falls back to the `ddgs` package, which requires no key but is less reliable for production use.

The ingestion layer is deliberately conservative: it does not invent effective dates, deadlines, obligations or applicability. If the source page does not support a field, that field remains unknown. The live record keeps the source URL and an evidence excerpt.

## Initial official source registry

The starter includes source-registry entries for:

- EUR-Lex recent legal acts
- Netherlands Officiële bekendmakingen
- Netherlands Wetten.overheid.nl

These entries are source portals only. Actual findings are created from live retrieval/search rather than from seeded legislation.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## Environment variables

```env
GITHUB_TOKEN=
COMPLIANCE_DB_PATH=compliance.db
AUTO_WEB_DISCOVERY=true
AUTO_WEB_DISCOVERY_INTERVAL_MINUTES=60
AUTO_WEB_MAX_RESULTS=18
AUTO_WEB_SOURCE_LINKS=12
AUTO_WEB_TIMEOUT_SECONDS=20
TAVILY_API_KEY=
```

`TAVILY_API_KEY` is optional. For a stable production deployment it is recommended because no-key search backends can be rate-limited or change behavior.

## Deploy from GitHub

For the first public version, use Streamlit Community Cloud:

1. Upload every file in this package to the root of a GitHub repository.
2. Create a Streamlit Community Cloud application from the repository.
3. Set the main file to `app.py`.
4. Add secrets/environment variables in the deployment settings.
5. Add `GITHUB_TOKEN` only if GitHub Copilot analysis is required.
6. Add `TAVILY_API_KEY` if you want the recommended production web-search provider.

GitHub Pages cannot execute the Python regulatory pipeline. The code can remain entirely in GitHub while Streamlit Community Cloud provides the public URL.

## Light and dark mode

The custom CSS does not hardcode a white application surface. It inherits Streamlit's active `background-color`, `secondary-background-color`, and `text-color` theme variables, while keeping purple/yellow as brand accents. This lets the same screens remain coherent in both light and dark mode.

## AI configuration

AI is optional. Python performs the deterministic executive metrics and summary. GitHub Copilot is used only for clearly labelled AI interpretation. AI prompts prohibit inventing laws, deadlines, tax rates, legislative references, authorities, product scope or applicability.

## Flat repository structure

Every item is a root-level file:

```text
app.py                         Streamlit entry point
app_styles.py                  Theme-aware vidaXL/Pigment-inspired styling
ai_copilot_service.py          Grounded GitHub Copilot analysis
config_settings.py             Taxonomy, DB path and web-monitoring settings
core_analytics.py              Deterministic Python executive analysis
core_models.py                 Core data models
core_source_adapters.py        Source-adapter interface
services_web_discovery.py      Automatic public-web search and source discovery
db_repository.py               SQLite persistence, runtime state and edit history
db_seed.py                     Verified source-registry seed only
services_exports.py            PDF and PPTX exports
services_source_health.py      Source-health checks
test_analytics.py              Analytics tests
test_repository.py             Persistence/history tests
test_web_discovery.py          Conservative web-processing tests
source-health-workflow.yml      Optional workflow reference
streamlit-config-reference.toml Optional Streamlit theme reference
```

## Production note

SQLite is suitable for a starter/single-instance deployment. For a multi-user application or scheduled monitoring that must survive instance restarts, replace the persistence layer with PostgreSQL. The repository functions are isolated so the UI and analysis layers do not need to be rewritten.

## Disclaimer

This application supports regulatory monitoring and internal analysis. Source-derived records can still require human verification. AI-generated analysis is informational only and is not legal or tax advice. Material conclusions should be checked against the authoritative primary source.

## Dashboard exports

The PDF and PowerPoint buttons export the **current Overview view**, using the same filtered records, KPI row, deterministic executive summary, priority developments, impact profile, confirmed deadlines, and visible AI analysis. The export styling follows the current Streamlit light/dark theme when that theme information is available.


## Tavily search diagnostics

The Sources page now shows whether the Tavily secret is detected, which search provider was actually used, and any provider error. Use **Test Tavily** to verify the API connection and **Search the web now** to force a fresh monitoring cycle. Adding a Tavily key automatically invalidates the previous DDGS monitoring interval so the next app session searches again immediately.

The Tavily integration uses Bearer authentication and first-class `include_domains` restrictions for registered official sources. Search-result evidence is retained even when an official website blocks a follow-up HTML request.
