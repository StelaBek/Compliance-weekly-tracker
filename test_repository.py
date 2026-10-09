from pathlib import Path
from db_repository import init_db,upsert_finding,versions,get_finding

def base():
    return {"id":"X1","is_demo":False,"jurisdiction":"EU","geographic_level":"EU","authority":"A","source_name":"S","source_url":"u","original_title":"T","english_title":"T","original_language":"en","business_impact":"Low","compliance_domain":"Other","category":"Other","legislative_status":"Unknown"}

def test_edit_preserves_history(tmp_path:Path):
    p=tmp_path/"x.db"; init_db(p); r=base(); upsert_finding(r,p,"seed"); r["business_impact"]="High"; upsert_finding(r,p,"manual"); assert get_finding("X1",p)["business_impact"]=="High"; h=versions("X1",p); assert "business_impact" in h["field_name"].tolist()
