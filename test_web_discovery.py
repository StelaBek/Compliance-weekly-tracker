from services_web_discovery import _relevance, _finding_from_page


def test_relevance_classifies_packaging():
    score, category, domain = _relevance("Official regulation on packaging and packaging waste with EPR reporting requirements")
    assert score > 0
    assert category in {"Packaging", "EPR"}
    assert domain in {"Environmental compliance", "Product compliance"}


def test_finding_keeps_unknown_dates_unknown():
    page = {
        "title": "Official notice on VAT electronic invoicing",
        "text": "This official notice concerns VAT and electronic invoicing requirements.",
        "url": "https://example.gov.test/notice-1",
        "publication_date": None,
    }
    source = {
        "jurisdiction": "Testland",
        "authority": "Test authority",
        "name": "Test official portal",
        "language": "English",
    }
    record = _finding_from_page(page, source)
    assert record is not None
    assert record["publication_date"] is None
    assert record["effective_date"] is None
    assert record["compliance_deadline"] is None
    assert record["source_url"] == page["url"]
