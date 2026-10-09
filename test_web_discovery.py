from services_web_discovery import _relevance, _finding_from_page, reporting_window


def test_relevance_classifies_packaging():
    score, category, domain = _relevance("Official regulation on packaging and packaging waste with EPR reporting requirements")
    assert score > 0
    assert category in {"Packaging", "Waste / EPR"}
    assert domain in {"Environmental compliance", "Product compliance"}


def test_finding_rejects_unverified_missing_date_and_reference():
    page = {
        "title": "Official notice on product requirements",
        "text": "This official notice concerns product requirements.",
        "url": "https://example.gov.test/notice-1",
        "publication_date": None,
    }
    source = {"jurisdiction": "Testland", "authority": "Test authority", "name": "Test official portal", "language": "English"}
    assert _finding_from_page(page, source) is None


def test_finding_accepts_current_week_verified_material_update():
    start, end = reporting_window()
    page = {
        "title": "Regulation (EU) 2026/1234 published packaging update",
        "text": f"Regulation (EU) 2026/1234 was published on {end}. The update concerns packaging labelling and reporting obligations for manufacturers and importers. It applies from 2027-01-01.",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1234",
        "publication_date": end,
    }
    source = {"jurisdiction": "European Union", "authority": "European Union", "name": "EUR-Lex", "language": "English"}
    record = _finding_from_page(page, source)
    assert record is not None
    assert record["jurisdiction"] == "EU"
    assert record["publication_update_date"] == end
    assert record["legislation"]
    assert record["summary"].count(".") >= 2
    assert "manufacturers" in record["scope"]
