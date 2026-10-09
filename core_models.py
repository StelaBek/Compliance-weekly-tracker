from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Finding:
    id: str
    is_demo: bool
    jurisdiction: str
    geographic_level: str
    authority: str
    source_name: str
    source_url: str
    original_title: str
    english_title: str
    original_language: str
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    compliance_deadline: Optional[str] = None
    legislative_status: str = "Unknown"
    instrument_type: str = "Unknown"
    compliance_domain: str = "Other"
    category: str = "Other"
    subcategory: str = ""
    affected_parties: str = ""
    key_obligations: str = ""
    key_changes: str = ""
    business_impact: str = "Informational"
    recommended_follow_up: str = ""
    confidence_score: Optional[float] = None
    evidence_excerpt: str = ""
    retrieved_at: Optional[str] = None
    ai_summary: str = ""
    ai_analysis: str = ""
    user_notes: str = ""
    publication_update_date: Optional[str] = None
    effective_application_date: Optional[str] = None
    scope: str = ""
    summary: str = ""
    legislation: str = ""
    status: str = "Unknown"
    business_action: str = ""
    def to_dict(self):
        return asdict(self)
