from datetime import date
import pandas as pd
from core_analytics import calculate_metrics, executive_summary, deadline_frame

def sample():
    return pd.DataFrame([
        {"jurisdiction":"EU","business_impact":"High","compliance_deadline":"2026-11-01","category":"Packaging"},
        {"jurisdiction":"NL","business_impact":"Low","compliance_deadline":"2027-10-01","category":"VAT"},
    ])

def test_metrics_are_deterministic():
    m=calculate_metrics(sample(),today=date(2026,10,1)); assert m=={"total":2,"high_critical":1,"next_90_days":1,"jurisdictions":2}

def test_summary_uses_python_values():
    s=executive_summary(sample(),today=date(2026,10,1)); assert "2 regulatory findings" in s; assert "1 is classified" in s

def test_deadline_filter():
    assert len(deadline_frame(sample(),today=date(2026,10,1),horizon_days=60))==1
