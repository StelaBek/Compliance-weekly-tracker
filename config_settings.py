from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("COMPLIANCE_DB_PATH", ROOT / "compliance.db"))

BRAND = {
    "purple": "#A20B8D",
    "purple_dark": "#6F075F",
    "yellow": "#FFC400",
}

IMPACT_ORDER = ["Informational", "Low", "Medium", "High", "Critical"]
DOMAINS = ["Product compliance", "Tax compliance", "Customs", "Environmental compliance", "Other"]
STATUSES = [
    "Proposal", "Consultation", "Adopted", "Published", "Entered into force",
    "Applicable", "Implementation pending", "National transposition required",
    "Amended", "Repealed", "Unknown",
]

AUTO_WEB_DISCOVERY = os.environ.get("AUTO_WEB_DISCOVERY", "true").strip().lower() in {"1", "true", "yes", "on"}
AUTO_WEB_DISCOVERY_INTERVAL_MINUTES = int(os.environ.get("AUTO_WEB_DISCOVERY_INTERVAL_MINUTES", "60"))
AUTO_WEB_MAX_RESULTS = int(os.environ.get("AUTO_WEB_MAX_RESULTS", "18"))
AUTO_WEB_SOURCE_LINKS = int(os.environ.get("AUTO_WEB_SOURCE_LINKS", "12"))
AUTO_WEB_TIMEOUT_SECONDS = int(os.environ.get("AUTO_WEB_TIMEOUT_SECONDS", "20"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()

# Queries intentionally stay broad. Final ingestion still requires an official/registered source.
COMPLIANCE_SEARCH_TERMS = [
    "product safety", "CE marking", "conformity assessment", "labelling", "packaging",
    "ecodesign", "energy labelling", "REACH", "RoHS", "batteries", "EPR",
    "digital product passport", "right to repair", "VAT", "indirect tax", "customs",
    "import VAT", "e-invoicing", "electronic invoicing", "digital reporting",
    "excise", "registration threshold", "reporting obligation",
]

# Used only for discovery prioritisation, never as proof that a result is official.
JURISDICTIONS = [
    "European Union", "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
    "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland",
    "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden", "Iceland",
    "Liechtenstein", "Norway", "Switzerland", "United Kingdom",
]
