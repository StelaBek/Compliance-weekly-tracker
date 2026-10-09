from config_settings import JURISDICTION_REGISTRY
from services_web_discovery import _one_paragraph_summary

def test_required_scope_is_complete():
    names = {x["name"] for x in JURISDICTION_REGISTRY}
    assert "European Union" in names
    assert "United Kingdom" in names
    assert "Switzerland" in names
    assert {"Iceland", "Liechtenstein", "Norway"}.issubset(names)
    assert len([x for x in JURISDICTION_REGISTRY if x["level"] == "National"]) == 32

def test_summary_is_one_paragraph_and_grounded():
    page={"title":"Packaging decree", "text":"The authority published a new packaging reporting rule. The measure applies from the date specified in the official notice."}
    source={"jurisdiction":"Netherlands"}
    summary=_one_paragraph_summary(page, source, "Packaging", "Product compliance")
    assert "national-level" in summary
    assert "Packaging" in summary
    assert "\n" not in summary
