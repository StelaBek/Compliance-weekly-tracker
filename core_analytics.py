from __future__ import annotations
from datetime import date
import pandas as pd
from config_settings import IMPACT_ORDER

def _to_date(value):
    if value is None or value == "" or pd.isna(value): return None
    try: return pd.to_datetime(value).date()
    except Exception: return None

def add_deadline_metrics(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    out = df.copy(); today = today or date.today()
    series = out.get("compliance_deadline", pd.Series(index=out.index, dtype=object))
    out["days_to_deadline"] = series.map(lambda x: (_to_date(x)-today).days if _to_date(x) else None)
    return out

def calculate_metrics(df: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    if df.empty: return {"total":0,"high_critical":0,"next_90_days":0,"jurisdictions":0}
    d=add_deadline_metrics(df,today)
    high=int(d["business_impact"].isin(["High","Critical"]).sum()) if "business_impact" in d else 0
    upcoming=int(d["days_to_deadline"].map(lambda x: x is not None and 0 <= x <= 90).sum())
    jurisdictions=int(d["jurisdiction"].nunique()) if "jurisdiction" in d else 0
    return {"total":len(d),"high_critical":high,"next_90_days":upcoming,"jurisdictions":jurisdictions}

def executive_summary(df: pd.DataFrame, today: date | None = None) -> str:
    m=calculate_metrics(df,today)
    if m["total"]==0: return "No regulatory findings match the current filters."
    pieces=[f"{m['total']} regulatory finding{'s' if m['total'] != 1 else ''} match the current view.",f"{m['high_critical']} {'is' if m['high_critical'] == 1 else 'are'} classified as high or critical impact.",f"{m['next_90_days']} {'has' if m['next_90_days'] == 1 else 'have'} a confirmed compliance deadline within the next 90 days.",f"The view covers {m['jurisdictions']} jurisdiction{'s' if m['jurisdictions'] != 1 else ''}."]
    if "category" in df and not df["category"].dropna().empty:
        top=df["category"].replace("",pd.NA).dropna().value_counts()
        if not top.empty: pieces.append(f"The most frequently represented category is {top.index[0]} ({int(top.iloc[0])} findings).")
    return " ".join(pieces)

def impact_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "business_impact" not in df: return pd.DataFrame(columns=["Impact","Count"])
    counts=df["business_impact"].value_counts().reindex(IMPACT_ORDER,fill_value=0)
    return counts.rename_axis("Impact").reset_index(name="Count")

def deadline_frame(df: pd.DataFrame, today: date | None = None, horizon_days: int = 365) -> pd.DataFrame:
    if df.empty: return df.copy()
    out=add_deadline_metrics(df,today)
    return out[out["days_to_deadline"].map(lambda x: x is not None and 0 <= x <= horizon_days)].sort_values("days_to_deadline")
