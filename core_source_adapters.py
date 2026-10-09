from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import requests
from bs4 import BeautifulSoup

@dataclass
class SourceDocument:
    source_id: str
    jurisdiction: str
    authority: str
    document_id: str
    title: str
    publication_date: str | None
    url: str
    document_type: str
    language: str
    raw_text: str
    metadata: dict

class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self) -> list[SourceDocument]: raise NotImplementedError

class GenericHtmlAdapter(SourceAdapter):
    """Basic adapter for a verified official HTML page. It deliberately does not infer legal status, dates or scope."""
    def __init__(self,source_id,jurisdiction,authority,url,language="Unknown"):
        self.source_id=source_id; self.jurisdiction=jurisdiction; self.authority=authority; self.url=url; self.language=language
    def fetch(self):
        response=requests.get(self.url,timeout=30,headers={"User-Agent":"ComplianceIntelligence/1.0"}); response.raise_for_status()
        soup=BeautifulSoup(response.text,"html.parser"); title=soup.title.string.strip() if soup.title and soup.title.string else self.url
        text=" ".join(soup.stripped_strings); digest=hashlib.sha256((self.url+text[:5000]).encode("utf-8",errors="ignore")).hexdigest()[:24]
        return [SourceDocument(self.source_id,self.jurisdiction,self.authority,digest,title,None,self.url,"HTML page",self.language,text,{"retrieved_at":datetime.now(timezone.utc).isoformat()})]
