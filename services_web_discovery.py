from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from urllib.parse import urljoin, urlparse
import json
import os
import re

import requests
from bs4 import BeautifulSoup

from config_settings import (
    AUTO_WEB_DISCOVERY,
    AUTO_WEB_DISCOVERY_INTERVAL_MINUTES,
    AUTO_WEB_MAX_RESULTS,
    AUTO_WEB_SOURCE_LINKS,
    AUTO_WEB_TIMEOUT_SECONDS,
    AUTO_WEB_RESULTS_PER_JURISDICTION,
    COMPLIANCE_SEARCH_TERMS,
    JURISDICTIONS,
    JURISDICTION_REGISTRY,
    PRODUCT_CATEGORIES,
    REPORT_START_DATE,
)
from db_repository import (
    get_runtime_state,
    list_sources,
    set_runtime_state,
    upsert_finding,
    upsert_source,
)

USER_AGENT = "ComplianceIntelligence/1.2 (+official-source-monitoring)"
SEARCH_GROUPS = [
    "published amended adopted officially updated product safety CE marking market surveillance packaging ecodesign batteries EPR digital product passport implementing delegated guidance enforcement deadline",
    "published amended adopted officially updated VAT indirect tax customs e-invoicing excise reporting implementing guidance enforcement deadline",
]

OFFICIAL_DOMAIN_HINTS = (
    ".gov.", ".gouv.", ".gv.", ".gov", ".government.", ".bund.de", ".admin.ch",
    ".europa.eu", "europa.eu", "overheid.nl", "officielebekendmakingen.nl",
    "legislation.gov.uk", "service-public.fr", "legifrance.gouv.fr",
    "fgov.be", "gov.pl", "gov.ie", "gov.mt", "gov.cy", "gov.gr", "gov.si",
    "gov.sk", "gov.hr", "gov.bg", "gov.ro", "gov.pt", "gov.lv", "gov.lt",
    "gov.ee", "gov.hu", "gov.cz", "gov.fi", "gov.se", "regjeringen.no",
    "lovdata.no", "government.is", "llv.li", "boe.es", "gazzettaufficiale.it",
    "ris.bka.gv.at", "gesetze-im-internet.de", "regeringen.se", "riksdagen.se",
)

# Terms used only for relevance detection. This deliberately includes common
# non-English legal/compliance wording because authoritative national sources
# are often not written in English.
MULTILINGUAL_TERMS = [
    "productveiligheid", "verpakking", "verpakkingen", "afval", "milieubelasting", "douane", "belasting", "btw", "wet", "regeling", "besluit", "staatsblad", "staatscourant",
    "produktsicherheit", "verpackung", "mehrwertsteuer", "umsatzsteuer", "zoll", "gesetz", "verordnung",
    "sécurité des produits", "emballage", "tva", "douane", "décret", "arrêté", "loi",
    "sicurezza dei prodotti", "imballaggi", "iva", "dogana", "decreto", "legge",
    "seguridad de los productos", "envases", "iva", "aduanas", "decreto", "ley",
    "bezpieczeństwo produktów", "opakowania", "vat", "cło", "ustawa", "rozporządzenie",
]
RELEVANCE_TERMS = list(dict.fromkeys(COMPLIANCE_SEARCH_TERMS + MULTILINGUAL_TERMS))

CATEGORY_RULES = [
    ("General Product Safety", ["general product safety", "gpsr"]),
    ("Product Safety", ["product safety", "productveiligheid", "produktsicherheit", "sécurité des produits", "sicurezza dei prodotti", "seguridad de los productos", "bezpieczeństwo produktów"]),
    ("CE Marking", ["ce marking", "ce-marking", "ce mark"]),
    ("Market Surveillance", ["market surveillance", "market-surveillance"]),
    ("Machinery", ["machinery", "machine regulation", "maschinen", "machines"]),
    ("Electrical Safety / LVD", ["low voltage directive", "lvd", "electrical safety"]),
    ("EMC", ["electromagnetic compatibility", " emc "] ),
    ("Radio Equipment", ["radio equipment", "red directive"]),
    ("Batteries", ["battery", "batteries", "battery regulation"]),
    ("Ecodesign", ["ecodesign", "eco-design"]),
    ("Energy Labelling", ["energy labelling", "energy labeling"]),
    ("Construction Products", ["construction products", "construction product regulation", "cpr"]),
    ("Chemicals / REACH", ["reach", "chemical restriction", "chemicals"]),
    ("RoHS", ["rohs", "restriction of hazardous substances"]),
    ("Packaging", ["packaging", "packaging waste", "verpakking", "verpakkingen", "verpackung", "emballage", "imballaggi", "envases", "opakowania", "ppwr"]),
    ("Waste / EPR", ["extended producer responsibility", "epr", "waste", "producer responsibility"]),
    ("Digital Product Passport", ["digital product passport", "dpp"]),
    ("Consumer Protection", ["consumer protection", "consumer rights"]),
    ("Cybersecurity", ["cybersecurity", "cyber resilience", "cra regulation"]),
    ("Sustainability", ["sustainability", "sustainable products"]),
    ("Environmental Compliance", ["environmental compliance", "environmental requirement", "emissions"]),
]


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    published_date: str | None = None
    score: float | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tavily_key() -> str:
    # Read dynamically rather than only once at module import. This is useful on
    # Streamlit Cloud when secrets are changed without rebuilding the repository.
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        if "TAVILY_API_KEY" in st.secrets:
            return str(st.secrets["TAVILY_API_KEY"]).strip()
    except Exception:
        pass
    return ""


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""


def _registered_host_match(url: str, source_url: str) -> bool:
    host = _host(url)
    source_host = _host(source_url)
    return bool(host and source_host and (host == source_host or host.endswith("." + source_host)))


def _looks_official_domain(url: str) -> bool:
    host = _host(url)
    wrapped = "." + host
    return any(hint in wrapped or host.endswith(hint.lstrip(".")) for hint in OFFICIAL_DOMAIN_HINTS)


def _normalise_date(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", str(value))
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # Tavily may return RFC-style dates.
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(str(value))
        return dt.date().isoformat()
    except Exception:
        return None



def reporting_window(now: datetime | None = None) -> tuple[str, str]:
    """Return the current ISO reporting week (Monday through today), never before 2026-01-01."""
    now = now or datetime.now(timezone.utc)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    floor = datetime.fromisoformat(REPORT_START_DATE).date()
    if monday < floor:
        monday = floor
    return monday.isoformat(), today.isoformat()


def _parse_iso_date(value: str | None):
    value = _normalise_date(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def _date_in_reporting_week(value: str | None) -> bool:
    d = _parse_iso_date(value)
    if d is None:
        return False
    start, end = reporting_window()
    return datetime.fromisoformat(start).date() <= d <= datetime.fromisoformat(end).date()


def _extract_date_from_text(text: str) -> str | None:
    text = _clean_sentence_text(text)
    patterns = [
        r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b",
        r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b",
    ]
    for i, pattern in enumerate(patterns):
        m = re.search(pattern, text)
        if m:
            if i == 0:
                y, mo, d = map(int, m.groups())
            else:
                d, mo, y = map(int, m.groups())
            try:
                return datetime(y, mo, d).date().isoformat()
            except ValueError:
                pass
    months = {m.lower(): i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}
    m = re.search(r"\b(0?[1-9]|[12]\d|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", text, flags=re.I)
    if m:
        try:
            return datetime(int(m.group(3)), months[m.group(2).lower()], int(m.group(1))).date().isoformat()
        except ValueError:
            pass
    return None


def _extract_legal_reference(text: str) -> str | None:
    """Conservative legal-reference extractor. Findings without a verifiable reference are rejected."""
    text = _clean_sentence_text(text)
    patterns = [
        r"\b(?:Commission\s+)?(?:Delegated\s+|Implementing\s+)?(?:Regulation|Directive|Decision)\s*\((?:EU|EC|EEC)\)\s*(?:No\.?\s*)?\d{4}/\d{1,5}\b",
        r"\b(?:Regulation|Directive|Decision)\s*\((?:EU|EC|EEC)\)\s*\d{4}/\d{1,5}\b",
        r"\bCELEX[:\s]*[0-9A-Z]{8,14}\b",
        r"\b(?:Act|Law|Decree|Regulation|Order|Ordinance|Statutory Instrument|S\.?I\.?)\s+(?:No\.?\s*)?\d{1,5}(?:[/.-]\d{2,4})?\b",
        r"\b(?:No\.?|Nr\.?|N°)\s*\d{1,5}[/-]20\d{2}\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            return m.group(0).strip()
    return None


def _material_update_type(text: str) -> str | None:
    lower = text.lower()
    mapping = [
        ("Amended", ["amend", "corrigendum", "revised", "modif", "änder", "wijzig"]),
        ("Adopted", ["adopted", "approved", "adoption"]),
        ("Published", ["published", "publication", "official journal", "official gazette"]),
        ("Official guidance", ["guidance", "guideline", "official guidance", "faq"]),
        ("Implementing act", ["implementing act", "implementing regulation", "implementing decision"]),
        ("Delegated act", ["delegated act", "delegated regulation", "delegated decision"]),
        ("Enforcement development", ["enforcement", "market surveillance action", "penalty", "sanction"]),
        ("Compliance milestone", ["deadline", "transition period", "transitional period", "becomes applicable", "application date", "enters into force", "entry into force"]),
        ("Official update", ["updated", "update", "new version"]),
    ]
    for label, terms in mapping:
        if any(term in lower for term in terms):
            return label
    return None


def _extract_effective_application_date(text: str) -> str | None:
    lower = text.lower()
    anchors = ["applicable from", "applies from", "application date", "enter into force", "enters into force", "effective from", "deadline", "transition period"]
    for anchor in anchors:
        pos = lower.find(anchor)
        if pos >= 0:
            date = _extract_date_from_text(text[pos:pos+260])
            if date and date >= REPORT_START_DATE:
                return date
    return None


def _scope_from_evidence(text: str, jurisdiction: str, category: str) -> str:
    lower = text.lower()
    operators = []
    pairs = [
        ("manufacturers", ["manufacturer", "manufacturers"]),
        ("importers", ["importer", "importers"]),
        ("distributors", ["distributor", "distributors"]),
        ("authorised representatives", ["authorised representative", "authorized representative"]),
        ("fulfilment service providers", ["fulfilment service provider", "fulfillment service provider"]),
        ("online marketplaces", ["online marketplace", "marketplace provider"]),
        ("retailers", ["retailer", "retailers"]),
    ]
    for label, words in pairs:
        if any(w in lower for w in words):
            operators.append(label)
    obligations = []
    for label, words in [
        ("testing", ["test", "testing"]), ("labelling", ["label", "labelling", "labeling"]),
        ("documentation", ["documentation", "technical file", "declaration of conformity"]),
        ("registration", ["register", "registration"]), ("reporting", ["reporting", "report"]),
        ("sustainability", ["sustainability", "ecodesign", "environmental"]),
        ("safety", ["safety", "hazard", "risk"]), ("market surveillance", ["market surveillance"]),
        ("restrictions", ["restriction", "prohibit", "ban"]),
    ]:
        if any(w in lower for w in words):
            obligations.append(label)
    op_text = ", ".join(operators) if operators else "the affected economic operators identified in the official source"
    obligation_text = ", ".join(obligations) if obligations else "the compliance obligations described in the official source"
    geo = "the European Union" if jurisdiction == "European Union" else jurisdiction
    return f"Applies to products or services within the {category} area where covered by the cited measure, in {geo}. The available official-source evidence identifies or may affect {op_text}. The material update concerns {obligation_text}; any product-level exclusions or sector-specific limits must be confirmed in the cited legal text."


def _summary_from_evidence(text: str, update_type: str, legislation: str, effective_date: str | None, jurisdiction: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", _clean_sentence_text(text)) if len(s.strip()) >= 35]
    evidence_sentence = sentences[0] if sentences else "The official source records a material compliance development during the reporting week."
    deadline = f" A confirmed effective, application or transition date is {effective_date}." if effective_date else " No effective or application date is treated as confirmed unless it is stated in the cited source."
    next_step = " Companies should review applicability, affected products and operational obligations against the cited official text and update compliance plans where necessary."
    return f"{legislation} was identified as a {update_type.lower()} affecting {jurisdiction}. {evidence_sentence}{deadline}{next_step}"


def _search_tavily(query: str, max_results: int, include_domains: list[str] | None = None) -> list[SearchHit]:
    key = _tavily_key()
    if not key:
        return []
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "topic": "general",
        "include_answer": False,
        "include_raw_content": False,
        "include_published_date": True,
    }
    if include_domains:
        payload["include_domains"] = include_domains
        payload["include_domains_mode"] = "restrict"
    # Focus the scheduled monitor on new material. If an older Tavily API version
    # rejects time_range, retry once without it rather than failing the weekly run.
    payload["time_range"] = "week"
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    response = requests.post(
        "https://api.tavily.com/search", headers=headers, json=payload,
        timeout=AUTO_WEB_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400 and "time_range" in payload:
        payload.pop("time_range", None)
        response = requests.post(
            "https://api.tavily.com/search", headers=headers, json=payload,
            timeout=AUTO_WEB_TIMEOUT_SECONDS,
        )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Tavily HTTP {response.status_code}: {detail}")
    data = response.json()
    return [
        SearchHit(
            str(item.get("title") or ""),
            str(item.get("url") or ""),
            str(item.get("content") or ""),
            _normalise_date(item.get("published_date")),
            float(item.get("score")) if item.get("score") is not None else None,
        )
        for item in data.get("results", [])
        if item.get("url")
    ]


def _search_ddgs(query: str, max_results: int) -> list[SearchHit]:
    try:
        from ddgs import DDGS
    except Exception:
        return []
    hits: list[SearchHit] = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                url = str(item.get("href") or item.get("url") or "")
                if url:
                    hits.append(SearchHit(str(item.get("title") or ""), url, str(item.get("body") or item.get("snippet") or "")))
    except Exception:
        return []
    return hits


def web_search(query: str, max_results: int = 8, include_domains: list[str] | None = None) -> tuple[list[SearchHit], str]:
    """Search the public web. Tavily is preferred and failures are recorded, not hidden."""
    if _tavily_key():
        try:
            hits = _search_tavily(query, max_results, include_domains=include_domains)
            set_runtime_state("last_search_provider", "Tavily")
            set_runtime_state("last_search_error", "")
            return hits, "Tavily"
        except Exception as exc:
            set_runtime_state("last_search_error", str(exc)[:700])
            # Fall back so monitoring can continue, but expose the Tavily error in Sources.
    hits = _search_ddgs(query, max_results)
    provider = "DDGS" if hits else "Unavailable"
    set_runtime_state("last_search_provider", provider)
    return hits, provider


def _download(url: str) -> tuple[str, str, dict[str, str]]:
    response = requests.get(url, timeout=AUTO_WEB_TIMEOUT_SECONDS, allow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en,*;q=0.7"})
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type and not content_type.startswith("text/"):
        return "", response.url, {"content_type": content_type}
    return response.text, response.url, {"content_type": content_type}


def _extract_page(url: str) -> dict | None:
    try:
        html, final_url, meta = _download(url)
    except Exception:
        return None
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = str(og_title.get("content")).strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        heading = soup.find(["h1", "h2"])
        title = heading.get_text(" ", strip=True) if heading else final_url
    text = re.sub(r"\s+", " ", " ".join(soup.stripped_strings)).strip()
    return {"title": title[:500], "text": text[:120000], "url": final_url, "publication_date": _extract_published_date(soup), **meta}


def _extract_published_date(soup: BeautifulSoup) -> str | None:
    names = [("property", "article:published_time"), ("name", "date"), ("name", "DC.date"),
             ("name", "dcterms.date"), ("name", "citation_publication_date"), ("itemprop", "datePublished")]
    values: list[str] = []
    for attr, value in names:
        node = soup.find(attrs={attr: value})
        if node:
            raw = node.get("content") or node.get("datetime") or node.get_text(" ", strip=True)
            if raw: values.append(str(raw))
    time_node = soup.find("time", attrs={"datetime": True})
    if time_node: values.append(str(time_node.get("datetime")))
    for raw in values:
        out = _normalise_date(raw)
        if out: return out
    return None


def _relevance(text: str) -> tuple[float, str, str]:
    lower = text.lower()
    hits = [term for term in RELEVANCE_TERMS if term.lower() in lower]
    if not hits:
        return 0.0, "Other", "Other"
    category = "Other"
    for label, terms in CATEGORY_RULES:
        if any(term in lower for term in terms):
            category = label; break
    tax_words = ["vat", "tax", "excise", "invoic", "filing", "reporting threshold", "btw", "iva", "tva", "belasting", "mehrwertsteuer", "umsatzsteuer"]
    customs_words = ["customs", "tariff", "import duty", "douane", "zoll", "dogana", "aduanas", "cło"]
    environmental_words = ["epr", "waste", "ecodesign", "environmental", "afval", "milieu"]
    if any(word in lower for word in customs_words): domain = "Customs"
    elif any(word in lower for word in tax_words): domain = "Tax compliance"
    elif any(word in lower for word in environmental_words): domain = "Environmental compliance"
    else: domain = "Product compliance"
    score = min(1.0, 0.38 + 0.08 * len(set(hits)))
    return score, category, domain


def _instrument_type(title: str) -> str:
    lower = title.lower()
    mapping = [
        ("Regulation", ["regulation", "verordening", "verordnung", "règlement", "regolamento", "reglamento"]),
        ("Directive", ["directive", "richtlijn", "richtlinie"]),
        ("Decision", ["decision", "besluit", "beschikking"]),
        ("Consultation", ["consultation"]), ("Guidance", ["guidance", "guideline"]),
        ("Notice", ["notice", "staatscourant"]), ("Act", ["act", "wet", "gesetz", "loi", "legge", "ley", "ustawa"]),
    ]
    for label, terms in mapping:
        if any(t in lower for t in terms): return label
    return "Unknown"


def _evidence_excerpt(text: str) -> str:
    lower = text.lower()
    positions = [(lower.find(term.lower()), term) for term in RELEVANCE_TERMS if lower.find(term.lower()) >= 0]
    if not positions: return text[:900]
    pos, _ = min(positions, key=lambda item: item[0])
    return text[max(0, pos-250):min(len(text), pos+650)].strip()[:900]


def _clean_sentence_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _one_paragraph_summary(page: dict, source: dict, category: str, domain: str) -> str:
    """Create a conservative one-paragraph finding summary from retrieved evidence only."""
    title = _clean_sentence_text(page.get("title"))
    body = _clean_sentence_text(page.get("text"))
    # Search-result snippets are already concise source-grounded evidence. Keep the
    # first few complete sentences instead of asking an LLM to fill missing context.
    sentences = re.split(r"(?<=[.!?])\s+", body)
    useful = []
    title_lower = title.lower()
    for sentence in sentences:
        sentence = sentence.strip(" -•\t")
        if len(sentence) < 35:
            continue
        if sentence.lower() == title_lower:
            continue
        useful.append(sentence)
        if len(" ".join(useful)) >= 520 or len(useful) >= 3:
            break
    evidence = " ".join(useful).strip()
    level = "EU-level" if source.get("jurisdiction") == "European Union" else "national-level"
    jurisdiction = source.get("jurisdiction") or "the relevant jurisdiction"
    intro = f"This {level} finding for {jurisdiction} concerns {category or domain or 'regulatory compliance'}."
    if evidence:
        return (intro + " " + evidence)[:900].strip()
    if title:
        return (intro + f" The official-source result is titled “{title}”. Review the cited source for the operative legal text, dates and scope.")[:900]
    return intro + " Review the cited official source for the operative legal text, dates and scope."


def _likely_official_hit(hit: SearchHit, jurisdiction: str) -> bool:
    """Conservative automated official-source test used for national discovery."""
    if _looks_official_domain(hit.url):
        return True
    text = f"{hit.title} {hit.snippet}".lower()
    official_clues = [
        "official gazette", "official journal", "government", "ministry", "parliament",
        "tax authority", "customs authority", "revenue service", "public administration",
        "boletín oficial", "gazzetta ufficiale", "journal officiel", "bundesgesetzblatt",
        "staatsblad", "staatscourant", "regjeringen", "riksdagen", "regeringen",
    ]
    return any(clue in text for clue in official_clues)


def _source_for_hit(hit: SearchHit, jurisdiction: str, geographic_level: str) -> dict | None:
    sources = list_sources()
    if not sources.empty:
        for row in sources.to_dict("records"):
            if row.get("jurisdiction") == jurisdiction and _registered_host_match(hit.url, row.get("url") or ""):
                return row
    if geographic_level == "EU":
        host = _host(hit.url)
        if not (host.endswith("europa.eu") or host.endswith("eur-lex.europa.eu")):
            return None
    elif not _looks_official_domain(hit.url):
        # For new national sources, require an official/government domain signal.
        # Textual clues alone are not enough to create a verified finding.
        return None
    host = _host(hit.url)
    if not host:
        return None
    sid = "AUTO-" + sha256((jurisdiction + host).encode("utf-8")).hexdigest()[:18].upper()
    source = {
        "id": sid, "jurisdiction": jurisdiction, "authority": "Official authority - verify exact issuer",
        "name": f"Official source — {host}", "url": f"{urlparse(hit.url).scheme or 'https'}://{host}/",
        "source_type": "Automatically discovered official-source candidate", "language": "Unknown",
        "verification_status": "verified official source", "retrieval_method": "Weekly web discovery",
        "active": True, "last_success": _now(), "last_failure": None, "error_state": None,
        "last_checked": _now(), "discovered_automatically": True,
        "discovery_reason": f"Automatically selected during the weekly {jurisdiction} scan because the result showed official/government source signals. Review remains available in Sources.",
    }
    upsert_source(source)
    return source


def _business_action_for(category: str, update_type: str) -> str:
    actions = {
        "Product Safety": "Review product risk assessments, technical documentation and corrective-action processes for affected products.",
        "General Product Safety": "Confirm GPSR applicability, responsible-person information, traceability and online product information for affected consumer products.",
        "CE Marking": "Review conformity-assessment routes, declarations of conformity, technical files and CE-marking requirements.",
        "Market Surveillance": "Review evidence packs, authority-response procedures, traceability and corrective-action readiness.",
        "Machinery": "Assess machinery scope, conformity assessment, technical documentation and instructions against the updated requirements.",
        "Electrical Safety / LVD": "Review electrical-safety conformity evidence, standards, testing and declarations for affected electrical products.",
        "EMC": "Review EMC testing, standards, technical documentation and declarations for affected equipment.",
        "Radio Equipment": "Review RED applicability, testing, software/cyber requirements and conformity documentation for radio equipment.",
        "Batteries": "Assess battery scope, labelling, due-diligence, information, registration and passport obligations where applicable.",
        "Ecodesign": "Assess affected product groups, performance requirements, information obligations and implementation timelines.",
        "Energy Labelling": "Review energy-label, product-database and supplier/dealer information requirements for affected products.",
        "Construction Products": "Review CPR scope, declarations, product information and conformity requirements for affected construction products.",
        "Chemicals / REACH": "Check substances, restrictions, candidate-list or authorisation impacts and update supplier/product documentation where necessary.",
        "RoHS": "Check restricted-substance limits, exemptions, technical evidence and declarations for affected EEE.",
        "Packaging": "Review packaging composition, labelling, recyclability, registration and reporting obligations for affected markets.",
        "Waste / EPR": "Review producer-registration, reporting, take-back and fee obligations for affected products and packaging streams.",
        "Digital Product Passport": "Assess product scope, data fields, identifiers, data carriers, system ownership and implementation timing.",
        "Consumer Protection": "Review customer information, sales practices, product claims and consumer-facing processes affected by the update.",
        "Cybersecurity": "Review product cybersecurity requirements, vulnerability handling, documentation and conformity obligations.",
        "Sustainability": "Assess sustainability information, performance, substantiation and supply-chain evidence requirements.",
        "Environmental Compliance": "Assess environmental restrictions, reporting, documentation and operational controls affected by the measure.",
    }
    base = actions.get(category, "Review applicability, affected products, required controls and implementation timing against the cited official source.")
    return f"{base} Record the {update_type.lower()} in the compliance change log and assign an owner if action is required."


def _finding_from_page(page: dict, source: dict) -> dict | None:
    """Build a finding only when recency, official source, date and legal reference are verifiable."""
    combined = _clean_sentence_text(f"{page.get('title','')} {page.get('text','')}")
    score, category, domain = _relevance(combined)
    if score < 0.42:
        return None

    url = page.get("url") or ""
    if not url or not source.get("name"):
        return None

    publication_update_date = _normalise_date(page.get("publication_date")) or _extract_date_from_text(combined)
    if not publication_update_date or publication_update_date < REPORT_START_DATE or not _date_in_reporting_week(publication_update_date):
        return None

    legislation = _extract_legal_reference(combined)
    if not legislation:
        return None

    update_type = _material_update_type(combined)
    if not update_type:
        return None

    effective_application_date = _extract_effective_application_date(combined)
    jurisdiction = source.get("jurisdiction") or "Unknown"
    geographic_level = "EU" if jurisdiction == "European Union" else "National"
    if category not in PRODUCT_CATEGORIES:
        category = "Other"

    scope = _scope_from_evidence(combined, jurisdiction, category)
    summary = _summary_from_evidence(combined, update_type, legislation, effective_application_date, "EU" if geographic_level == "EU" else jurisdiction)
    title = f"{legislation} — {category} {update_type.lower()}"
    business_action = _business_action_for(category, update_type)
    evidence = _evidence_excerpt(page.get("text") or combined)

    return {
        "id": "WEB-" + sha256((jurisdiction + legislation + publication_update_date + url).encode("utf-8", errors="ignore")).hexdigest()[:20].upper(),
        "is_demo": False,
        "jurisdiction": "EU" if geographic_level == "EU" else jurisdiction,
        "geographic_level": geographic_level,
        "authority": source.get("authority") or "Official authority",
        "source_name": source.get("name") or _host(url),
        "source_url": url,
        "original_title": page.get("title") or legislation,
        "english_title": title,
        "original_language": source.get("language") or "Unknown",
        "publication_date": publication_update_date,
        "effective_date": effective_application_date,
        "compliance_deadline": effective_application_date if update_type == "Compliance milestone" else None,
        "legislative_status": update_type,
        "instrument_type": _instrument_type(combined),
        "compliance_domain": domain,
        "category": category,
        "subcategory": None,
        "affected_parties": scope,
        "key_obligations": scope,
        "key_changes": summary,
        "business_impact": "Informational",
        "recommended_follow_up": business_action,
        "confidence_score": round(score, 2),
        "evidence_excerpt": evidence,
        "retrieved_at": _now(),
        "finding_summary": summary,
        "ai_summary": "",
        "ai_analysis": "",
        "user_notes": "",
        # New report contract fields requested by the tracker specification.
        "publication_update_date": publication_update_date,
        "effective_application_date": effective_application_date,
        "scope": scope,
        "summary": summary,
        "legislation": legislation,
        "status": update_type,
        "business_action": business_action,
    }


def _page_from_search_hit(hit: SearchHit) -> dict:
    return {"title": hit.title or hit.url, "text": hit.snippet or "", "url": hit.url,
            "publication_date": hit.published_date, "content_type": "search-result-evidence"}


def _candidate_links_from_source(source: dict) -> list[str]:
    try:
        html, final_url, _ = _download(source["url"])
    except Exception:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(final_url, anchor.get("href")); label = anchor.get_text(" ", strip=True)
        haystack = f"{label} {href}".lower()
        if not _registered_host_match(href, source["url"]): continue
        if any(term.lower() in haystack for term in RELEVANCE_TERMS) or any(token in haystack for token in ["legal", "regulation", "directive", "law", "act", "publication", "staatsblad", "staatscourant"]):
            links.append(href.split("#")[0])
        if len(links) >= AUTO_WEB_SOURCE_LINKS: break
    return list(dict.fromkeys(links))


def _search_registered_source(source: dict) -> tuple[list[SearchHit], list[str], str]:
    host = _host(source["url"])
    hits_out: list[SearchHit] = []
    provider = "Direct crawl"
    for group in SEARCH_GROUPS:
        # Tavily has first-class domain restriction. This is more reliable than
        # placing site:domain into the natural-language query.
        hits, used = web_search(group, max_results=max(5, AUTO_WEB_MAX_RESULTS // 3), include_domains=[host] if host else None)
        if hits: provider = used
        for hit in hits:
            if _registered_host_match(hit.url, source["url"]): hits_out.append(hit)
    direct = _candidate_links_from_source(source)
    direct.append(source["url"])
    # Preserve order and de-duplicate Tavily URLs.
    seen=set(); dedup=[]
    for h in hits_out:
        if h.url not in seen: dedup.append(h); seen.add(h.url)
    return dedup[:AUTO_WEB_MAX_RESULTS], list(dict.fromkeys(direct))[:AUTO_WEB_SOURCE_LINKS+1], provider


def ingest_registered_sources() -> dict:
    sources_df = list_sources(); findings=0; checked_urls=0; errors=[]; providers=set(); search_hits=0
    for source in sources_df.to_dict("records"):
        if not source.get("active") or source.get("verification_status") not in {"verified official source", "likely official source"}: continue
        try:
            hits, direct_urls, provider = _search_registered_source(source); providers.add(provider); search_hits += len(hits)
            successful=False; processed=set()
            # First use Tavily's returned evidence. This prevents an official site
            # blocking our follow-up GET from making a valid search result disappear.
            for hit in hits:
                checked_urls += 1; processed.add(hit.url)
                page = _page_from_search_hit(hit); successful=True
                finding = _finding_from_page(page, source)
                if finding: upsert_finding(finding, change_type="live-web-ingestion"); findings += 1
            # Then enrich with direct HTML when possible.
            for url in direct_urls:
                if url in processed: continue
                checked_urls += 1; page = _extract_page(url)
                if not page: continue
                successful=True
                finding = _finding_from_page(page, source)
                if finding: upsert_finding(finding, change_type="live-web-ingestion"); findings += 1
            source["last_checked"]=_now()
            if successful: source["last_success"]=source["last_checked"]; source["error_state"]=None
            else: source["last_failure"]=source["last_checked"]; source["error_state"]="No search results or readable HTML content were retrieved during this cycle."
            upsert_source(source)
        except Exception as exc:
            source["last_checked"]=_now(); source["last_failure"]=source["last_checked"]; source["error_state"]=str(exc)[:300]; upsert_source(source)
            errors.append(f"{source.get('name')}: {exc}")
    return {"findings": findings, "checked_urls": checked_urls, "search_hits": search_hits, "providers": sorted(providers), "errors": errors}


def scan_all_jurisdictions() -> dict:
    """Search EU and every national jurisdiction for material changes in the current reporting week."""
    total_findings = 0
    total_hits = 0
    rejected_unverified = 0
    providers = set()
    jurisdiction_reports = []
    week_start, week_end = reporting_window()

    event_terms = (
        "published amended adopted officially updated implementing act delegated act official guidance "
        "enforcement development compliance deadline transition milestone enters into force applicable"
    )
    product_terms = (
        "product safety CE marking market surveillance machinery LVD EMC radio equipment batteries "
        "ecodesign energy labelling construction products REACH RoHS packaging EPR digital product passport "
        "consumer protection cybersecurity sustainability environmental compliance"
    )

    for item in JURISDICTION_REGISTRY:
        jurisdiction = item["name"]
        level = item["level"]
        before = total_findings
        display_jurisdiction = "European Union" if level == "EU" else jurisdiction
        if level == "EU":
            queries = [
                f'official EU legislation {event_terms} {product_terms} "{week_start}" "{week_end}"',
                f'EUR-Lex European Commission delegated implementing guidance {product_terms} {event_terms} {week_start} {week_end}',
            ]
        else:
            queries = [
                f'official government gazette ministry regulator "{jurisdiction}" {event_terms} {product_terms} {week_start} {week_end}',
                f'official national legislation market surveillance authority "{jurisdiction}" {event_terms} product regulation {week_start} {week_end}',
            ]

        seen_urls = set()
        for query in queries:
            hits, provider = web_search(query, max_results=AUTO_WEB_RESULTS_PER_JURISDICTION)
            providers.add(provider)
            total_hits += len(hits)
            for hit in hits:
                if not hit.url or hit.url in seen_urls:
                    continue
                seen_urls.add(hit.url)
                source = _source_for_hit(hit, display_jurisdiction, level)
                if not source:
                    rejected_unverified += 1
                    continue
                source = dict(source)
                source["jurisdiction"] = display_jurisdiction
                page = _page_from_search_hit(hit)
                finding = _finding_from_page(page, source)
                if finding:
                    finding["geographic_level"] = level
                    finding["jurisdiction"] = "EU" if level == "EU" else jurisdiction
                    upsert_finding(finding, change_type="weekly-current-development-scan")
                    total_findings += 1
                else:
                    rejected_unverified += 1
        jurisdiction_reports.append({
            "jurisdiction": "EU" if level == "EU" else jurisdiction,
            "geographic_level": level,
            "findings": total_findings - before,
            "search_results": len(seen_urls),
        })

    return {
        "reporting_week_start": week_start,
        "reporting_week_end": week_end,
        "jurisdictions_checked": len(JURISDICTION_REGISTRY),
        "findings": total_findings,
        "search_hits": total_hits,
        "rejected_unverified_or_out_of_period": rejected_unverified,
        "providers": sorted(providers),
        "jurisdiction_reports": jurisdiction_reports,
    }


def discover_source_candidates(batch_size: int = 6) -> dict:
    cursor=int(get_runtime_state("source_discovery_cursor", "0") or 0)
    selected=[JURISDICTIONS[(cursor+i)%len(JURISDICTIONS)] for i in range(batch_size)]
    saved=0; provider_names=set(); existing_sources=list_sources(); existing_ids=set(existing_sources["id"].tolist()) if not existing_sources.empty else set()
    for jurisdiction in selected:
        query=f'official government legislation gazette tax authority product safety regulator "{jurisdiction}"'
        hits, provider=web_search(query, max_results=8); provider_names.add(provider); seen_hosts=set()
        for hit in hits:
            host=_host(hit.url)
            if not host or host in seen_hosts or not _looks_official_domain(hit.url): continue
            seen_hosts.add(host); sid="DISC-"+sha256((jurisdiction+host).encode("utf-8")).hexdigest()[:18].upper()
            if sid in existing_ids: continue
            upsert_source({"id":sid,"jurisdiction":jurisdiction,"authority":"Pending verification","name":hit.title[:180] or host,
                "url":f"{urlparse(hit.url).scheme or 'https'}://{host}/","source_type":"Automatically discovered candidate","language":"Unknown",
                "verification_status":"pending verification","retrieval_method":f"Web discovery ({provider})","active":False,
                "last_success":None,"last_failure":None,"error_state":None,"last_checked":_now(),"discovered_automatically":True,
                "discovery_reason":f"Found while searching for official regulatory sources for {jurisdiction}. Domain hint looked governmental; manual verification is still required."})
            existing_ids.add(sid); saved += 1
    set_runtime_state("source_discovery_cursor", str((cursor+batch_size)%len(JURISDICTIONS)))
    return {"jurisdictions":selected,"candidates":saved,"providers":sorted(provider_names)}


def _provider_fingerprint() -> str:
    return "tavily" if _tavily_key() else "ddgs"


def run_live_monitoring(force: bool=False) -> dict:
    if not AUTO_WEB_DISCOVERY and not force: return {"ran":False,"reason":"Automatic web discovery disabled"}
    last_raw=get_runtime_state("last_live_web_sync"); previous_provider=get_runtime_state("last_live_web_provider", "")
    current_provider=_provider_fingerprint()
    # A newly-added Tavily key must trigger a fresh crawl immediately rather than
    # waiting for the prior DDGS run's interval to expire.
    if last_raw and not force and previous_provider == current_provider:
        try:
            last=datetime.fromisoformat(last_raw)
            if datetime.now(timezone.utc)-last < timedelta(minutes=AUTO_WEB_DISCOVERY_INTERVAL_MINUTES):
                return {"ran":False,"reason":"Not due yet","last_sync":last_raw,"provider":current_provider}
        except Exception: pass
    started=_now()
    # 1) Scan already registered sources. 2) Independently scan every jurisdiction
    # in scope so national coverage does not depend on prior manual source setup.
    ingestion=ingest_registered_sources()
    jurisdiction_scan=scan_all_jurisdictions()
    finished=_now()
    report={"ran":True,"started":started,"finished":finished,"provider":current_provider,
            "ingestion":ingestion,"jurisdiction_scan":jurisdiction_scan,
            "discovery":{"jurisdictions":[r["jurisdiction"] for r in jurisdiction_scan["jurisdiction_reports"]],
                         "candidates":0,"providers":jurisdiction_scan.get("providers",[])}}
    set_runtime_state("last_live_web_sync", finished); set_runtime_state("last_live_web_provider", current_provider)
    set_runtime_state("last_live_web_report", json.dumps(report, default=str))
    return report


def last_live_report() -> dict:
    raw=get_runtime_state("last_live_web_report", "") or ""
    try: return json.loads(raw) if raw else {}
    except Exception: return {}


def search_diagnostics() -> dict:
    report=last_live_report(); ingestion=report.get("ingestion") or {}; scope=report.get("jurisdiction_scan") or {}
    return {
        "provider": get_runtime_state("last_search_provider", "Tavily" if _tavily_key() else "DDGS"),
        "tavily_configured": bool(_tavily_key()),
        "last_error": get_runtime_state("last_search_error", "") or (ingestion.get("errors") or [None])[0],
        "last_findings": int(ingestion.get("findings", 0) or 0) + int(scope.get("findings", 0) or 0),
        "last_search_hits": int(ingestion.get("search_hits", 0) or 0) + int(scope.get("search_hits", 0) or 0),
        "jurisdictions_checked": scope.get("jurisdictions_checked", 0),
        "last_sync": report.get("finished"),
    }


def tavily_connection_test() -> dict:
    if not _tavily_key(): return {"ok":False,"error":"TAVILY_API_KEY is not visible to the application."}
    try:
        hits=_search_tavily("EU product compliance regulation VAT packaging official journal", 5, include_domains=["eur-lex.europa.eu"])
        return {"ok":True,"result_count":len(hits),"sample":[h.title for h in hits[:3]]}
    except Exception as exc:
        return {"ok":False,"error":str(exc)}
