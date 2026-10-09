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
    "Published", "Amended", "Adopted", "Official update", "Implementing act",
    "Delegated act", "Official guidance", "Enforcement development",
    "Compliance milestone", "Entered into force", "Applicable", "Unknown",
]

AUTO_WEB_DISCOVERY = os.environ.get("AUTO_WEB_DISCOVERY", "true").strip().lower() in {"1", "true", "yes", "on"}
AUTO_WEB_DISCOVERY_INTERVAL_MINUTES = int(os.environ.get("AUTO_WEB_DISCOVERY_INTERVAL_MINUTES", "10080"))  # 7 days
AUTO_WEB_MAX_RESULTS = int(os.environ.get("AUTO_WEB_MAX_RESULTS", "18"))
AUTO_WEB_SOURCE_LINKS = int(os.environ.get("AUTO_WEB_SOURCE_LINKS", "12"))
AUTO_WEB_TIMEOUT_SECONDS = int(os.environ.get("AUTO_WEB_TIMEOUT_SECONDS", "20"))
AUTO_WEB_RESULTS_PER_JURISDICTION = int(os.environ.get("AUTO_WEB_RESULTS_PER_JURISDICTION", "6"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()

# Queries intentionally stay broad. Final ingestion still requires an official/registered source.
REPORT_START_DATE = "2026-01-01"

PRODUCT_CATEGORIES = [
    "Product Safety", "CE Marking", "Market Surveillance", "Machinery",
    "Electrical Safety / LVD", "EMC", "Radio Equipment", "Batteries",
    "Ecodesign", "Energy Labelling", "Construction Products", "Chemicals / REACH",
    "RoHS", "Packaging", "Waste / EPR", "Digital Product Passport",
    "Consumer Protection", "Cybersecurity", "General Product Safety",
    "Sustainability", "Environmental Compliance", "Other",
]

COMPLIANCE_SEARCH_TERMS = [
    "product safety", "CE marking", "conformity assessment", "labelling", "packaging",
    "ecodesign", "energy labelling", "REACH", "RoHS", "batteries", "EPR",
    "digital product passport", "right to repair", "VAT", "indirect tax", "customs",
    "import VAT", "e-invoicing", "electronic invoicing", "digital reporting",
    "excise", "registration threshold", "reporting obligation",
]

# Geographic scope: EU-level plus every EU Member State, EEA country, Switzerland and the UK.
# This registry drives the weekly scan, so every jurisdiction is checked in every scheduled cycle.
JURISDICTION_REGISTRY = [
    {"name": "European Union", "level": "EU", "group": "EU"},
    {"name": "Austria", "level": "National", "group": "EU"},
    {"name": "Belgium", "level": "National", "group": "EU"},
    {"name": "Bulgaria", "level": "National", "group": "EU"},
    {"name": "Croatia", "level": "National", "group": "EU"},
    {"name": "Cyprus", "level": "National", "group": "EU"},
    {"name": "Czechia", "level": "National", "group": "EU"},
    {"name": "Denmark", "level": "National", "group": "EU"},
    {"name": "Estonia", "level": "National", "group": "EU"},
    {"name": "Finland", "level": "National", "group": "EU"},
    {"name": "France", "level": "National", "group": "EU"},
    {"name": "Germany", "level": "National", "group": "EU"},
    {"name": "Greece", "level": "National", "group": "EU"},
    {"name": "Hungary", "level": "National", "group": "EU"},
    {"name": "Ireland", "level": "National", "group": "EU"},
    {"name": "Italy", "level": "National", "group": "EU"},
    {"name": "Latvia", "level": "National", "group": "EU"},
    {"name": "Lithuania", "level": "National", "group": "EU"},
    {"name": "Luxembourg", "level": "National", "group": "EU"},
    {"name": "Malta", "level": "National", "group": "EU"},
    {"name": "Netherlands", "level": "National", "group": "EU"},
    {"name": "Poland", "level": "National", "group": "EU"},
    {"name": "Portugal", "level": "National", "group": "EU"},
    {"name": "Romania", "level": "National", "group": "EU"},
    {"name": "Slovakia", "level": "National", "group": "EU"},
    {"name": "Slovenia", "level": "National", "group": "EU"},
    {"name": "Spain", "level": "National", "group": "EU"},
    {"name": "Sweden", "level": "National", "group": "EU"},
    {"name": "Iceland", "level": "National", "group": "EEA"},
    {"name": "Liechtenstein", "level": "National", "group": "EEA"},
    {"name": "Norway", "level": "National", "group": "EEA"},
    {"name": "Switzerland", "level": "National", "group": "Other"},
    {"name": "United Kingdom", "level": "National", "group": "Other"},
]
JURISDICTIONS = [item["name"] for item in JURISDICTION_REGISTRY]
