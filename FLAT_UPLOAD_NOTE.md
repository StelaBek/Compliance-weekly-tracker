# Flat upload note

Every item in this package is a file at repository root. Upload all files directly to GitHub.

Main Streamlit file: `app.py`

Automatic live web monitoring is implemented in `services_web_discovery.py`. Manual source entry remains available in the application.

GitHub Actions is the one exception to a flat repository: GitHub only executes workflow YAML after it is placed under `.github/workflows/`. The included workflow file is therefore a reference until you move it in GitHub.
