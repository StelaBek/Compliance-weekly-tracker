from __future__ import annotations

from pathlib import Path
import os
import sys
import threading

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import pandas as pd
import plotly.express as px
import streamlit as st

# Streamlit Community Cloud stores user secrets in st.secrets. Root-level
# secrets are often mirrored into the environment, but doing it explicitly
# here makes the Tavily configuration deterministic before config_settings is
# imported. The value is never displayed or written to the repository.
try:
    if not os.environ.get("TAVILY_API_KEY") and "TAVILY_API_KEY" in st.secrets:
        os.environ["TAVILY_API_KEY"] = str(st.secrets["TAVILY_API_KEY"]).strip()
except Exception:
    pass

from app_styles import apply_branding
from ai_copilot_service import analyze_finding, portfolio_brief
from config_settings import DOMAINS, IMPACT_ORDER, STATUSES, AUTO_WEB_DISCOVERY_INTERVAL_MINUTES
from core_analytics import calculate_metrics, executive_summary, impact_counts, deadline_frame
from db_repository import (
    init_db, list_findings, get_finding, upsert_finding, versions,
    list_sources, upsert_source,
)
from db_seed import seed_official_sources
from services_exports import build_pdf, build_pptx
from services_source_health import check_all_sources
from services_web_discovery import run_live_monitoring, last_live_report, search_diagnostics, tavily_connection_test

st.set_page_config(page_title="Compliance Intelligence", page_icon="✦", layout="wide")
apply_branding()
init_db()
seed_official_sources()

if "portfolio_ai" not in st.session_state:
    st.session_state.portfolio_ai = ""
if "selected_finding" not in st.session_state:
    st.session_state.selected_finding = None
if "auto_monitoring_attempted" not in st.session_state:
    st.session_state.auto_monitoring_attempted = False


def refresh():
    st.cache_data.clear()
    st.rerun()


def run_automatic_monitoring_once():
    """Start scheduled web monitoring without blocking the Streamlit page render.

    The previous implementation executed the full web crawl synchronously during
    page startup. On Streamlit Cloud this can take tens of seconds (or longer),
    leaving users with only the page title while network requests run. The crawl
    now runs in a daemon thread and writes only to SQLite/runtime state.
    """
    if st.session_state.auto_monitoring_attempted:
        return
    st.session_state.auto_monitoring_attempted = True

    def _worker():
        try:
            run_live_monitoring(force=False)
        except Exception as exc:
            # Do not crash or block the UI if a provider/source is unavailable.
            try:
                from db_repository import set_runtime_state
                set_runtime_state("last_live_web_background_error", str(exc)[:500])
            except Exception:
                pass

    threading.Thread(
        target=_worker,
        name="compliance-live-monitor",
        daemon=True,
    ).start()


def filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### Compliance Intelligence")
        report = last_live_report()
        if report.get("finished"):
            st.markdown(f'<span class="live-pill">Live web monitoring · last sync {report["finished"][:16].replace("T", " ")} UTC</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="live-pill">Live web monitoring enabled</span>', unsafe_allow_html=True)
        st.divider()
        query = st.text_input("Search", placeholder="law, category, authority…")
        jurisdictions = st.multiselect("Jurisdiction", sorted(df["jurisdiction"].dropna().unique().tolist()) if not df.empty else [])
        domains = st.multiselect("Domain", sorted(df["compliance_domain"].dropna().unique().tolist()) if not df.empty else [])
        impacts = st.multiselect("Impact", IMPACT_ORDER)
        st.divider()
        st.caption("AI-generated interpretation is labelled separately from source-derived information.")

    out = df.copy()
    if jurisdictions:
        out = out[out["jurisdiction"].isin(jurisdictions)]
    if domains:
        out = out[out["compliance_domain"].isin(domains)]
    if impacts:
        out = out[out["business_impact"].isin(impacts)]
    if query.strip() and not out.empty:
        q = query.strip().lower()
        mask = pd.Series(False, index=out.index)
        for col in ["english_title", "original_title", "authority", "category", "subcategory", "key_changes", "key_obligations"]:
            mask |= out[col].fillna("").astype(str).str.lower().str.contains(q, regex=False)
        out = out[mask]
    return out


def header():
    st.markdown(
        '<div class="hero"><div class="eyebrow">European product & tax compliance</div>'
        '<h1 style="margin:.2rem 0 0 0">Regulatory intelligence</h1></div>',
        unsafe_allow_html=True,
    )


def current_export_theme() -> str:
    """Best-effort match of the user's current Streamlit appearance."""
    try:
        theme = getattr(st.context, "theme", None)
        theme_type = getattr(theme, "type", None)
        if str(theme_type).lower() in {"light", "dark"}:
            return str(theme_type).lower()
    except Exception:
        pass
    return "light"


def brand_plotly(fig):
    """Apply the purple/yellow visual language without hard-coding a light canvas."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#7F7F8C"},
        hoverlabel={"bordercolor": "#A20B8D"},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(127,127,140,0.16)", zeroline=False)
    return fig


def overview(df: pd.DataFrame):
    m = calculate_metrics(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Relevant findings", m["total"])
    c2.metric("High / critical", m["high_critical"])
    c3.metric("Deadlines ≤90d", m["next_90_days"])
    c4.metric("Jurisdictions", m["jurisdictions"])

    st.markdown("### Executive summary")
    st.caption("Python-generated · deterministic from the current filtered dataset")
    st.write(executive_summary(df) if not df.empty else "No live findings are available in the current view yet. The application will keep monitoring configured official sources automatically.")

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown("### Priority developments")
        if df.empty:
            st.info("No live findings match the current filters yet. Use Sources to review automatic source discovery or run a web search immediately.")
        else:
            display = df[["id", "jurisdiction", "english_title", "category", "business_impact", "compliance_deadline"]].copy()
            display.columns = ["ID", "Jurisdiction", "Development", "Category", "Impact", "Deadline"]
            st.dataframe(display.head(12), use_container_width=True, hide_index=True)
            selected = st.selectbox("Open a development", [""] + df["id"].tolist(), format_func=lambda x: "Select…" if x == "" else x)
            if selected:
                st.session_state.selected_finding = selected
                st.rerun()

    with right:
        st.markdown("### Impact profile")
        counts = impact_counts(df)
        if not counts.empty:
            fig = px.bar(
                counts, x="Impact", y="Count", text_auto=True,
                color="Impact",
                category_orders={"Impact": IMPACT_ORDER},
                color_discrete_map={
                    "Informational": "#C7B2D3",
                    "Low": "#B98CC8",
                    "Medium": "#A20B8D",
                    "High": "#FFC400",
                    "Critical": "#6F075F",
                },
            )
            fig.update_layout(height=315, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            brand_plotly(fig)
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            st.caption("No impact profile yet.")

        st.markdown("### Next confirmed deadlines")
        d = deadline_frame(df, horizon_days=365)
        if d.empty:
            st.caption("No confirmed deadline in the next 12 months for this view.")
        else:
            st.dataframe(d[["compliance_deadline", "jurisdiction", "english_title", "business_impact"]].head(7), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### AI analysis")
    st.caption("Optional · grounded in visible structured records · informational only, not legal or tax advice")
    if st.session_state.portfolio_ai:
        st.markdown('<div class="ai-box"><b>✦ AI-generated portfolio analysis</b></div>', unsafe_allow_html=True)
        st.markdown(st.session_state.portfolio_ai)
    if st.button("Generate / refresh AI portfolio analysis", type="primary", disabled=df.empty):
        try:
            with st.spinner("Generating grounded AI analysis…"):
                st.session_state.portfolio_ai = portfolio_brief(df.to_dict("records"))
            st.rerun()
        except Exception as e:
            st.warning(f"AI analysis is unavailable: {e}")

    st.divider()
    st.markdown("### Export current result")
    st.caption("Exports mirror the current Overview layout and filtered records, including the visible executive summary, priority developments, impact profile, deadlines and AI analysis.")
    export_theme = current_export_theme()
    x1, x2 = st.columns(2)
    with x1:
        st.download_button("Download PDF", build_pdf(df, st.session_state.portfolio_ai, theme=export_theme), "compliance-intelligence.pdf", "application/pdf", use_container_width=True)
    with x2:
        st.download_button("Download PowerPoint", build_pptx(df, st.session_state.portfolio_ai, theme=export_theme), "compliance-intelligence.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)


def developments(df: pd.DataFrame):
    st.markdown("### Developments")
    st.caption("Edit analytical fields directly. Source provenance and version history are preserved.")
    if df.empty:
        st.info("No live findings are available yet.")
        return
    editable = ["id", "jurisdiction", "english_title", "compliance_domain", "category", "business_impact", "legislative_status", "compliance_deadline", "recommended_follow_up", "user_notes"]
    edited = st.data_editor(
        df[editable], use_container_width=True, hide_index=True, disabled=["id"], num_rows="fixed",
        column_config={
            "business_impact": st.column_config.SelectboxColumn(options=IMPACT_ORDER),
            "compliance_domain": st.column_config.SelectboxColumn(options=DOMAINS),
            "legislative_status": st.column_config.SelectboxColumn(options=STATUSES),
        },
    )
    if st.button("Save table edits", type="primary"):
        originals = {r["id"]: r for r in df.to_dict("records")}
        for r in edited.to_dict("records"):
            merged = originals[r["id"]].copy()
            merged.update(r)
            upsert_finding(merged, change_type="manual-table")
        st.success("Saved. Previous values remain in change history.")
        refresh()


def detail(finding_id: str):
    rec = get_finding(finding_id)
    if not rec:
        st.session_state.selected_finding = None
        st.rerun()
    if st.button("← Back to overview"):
        st.session_state.selected_finding = None
        st.rerun()

    st.markdown(f"## {rec.get('english_title') or rec.get('original_title')}")
    st.caption(f"{rec.get('jurisdiction')} · {rec.get('authority')} · {rec.get('legislative_status')}")
    official, analysis, history = st.tabs(["Official source & facts", "Editable analysis", "Change history"])

    with official:
        st.markdown('<div class="source-box"><b>Source-derived information</b><br>Use the primary-source link as the authoritative reference. Unknown fields stay unknown until supported by evidence.</div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            st.write("**Original title**", rec.get("original_title") or "—")
            st.write("**Source**", rec.get("source_name") or "—")
            st.write("**Authority**", rec.get("authority") or "—")
            st.write("**Language**", rec.get("original_language") or "—")
        with b:
            st.write("**Published**", rec.get("publication_date") or "—")
            st.write("**Effective**", rec.get("effective_date") or "—")
            st.write("**Deadline**", rec.get("compliance_deadline") or "—")
            st.write("**Extraction confidence**", rec.get("confidence_score") if rec.get("confidence_score") is not None else "—")
        if rec.get("source_url"):
            st.link_button("Open primary source", rec["source_url"])
        st.write("**Evidence excerpt**")
        st.info(rec.get("evidence_excerpt") or "No evidence excerpt stored.")

    with analysis:
        with st.form("edit-finding"):
            domain = st.selectbox("Compliance domain", DOMAINS, index=DOMAINS.index(rec.get("compliance_domain")) if rec.get("compliance_domain") in DOMAINS else len(DOMAINS) - 1)
            c1, c2 = st.columns(2)
            category = c1.text_input("Category", rec.get("category") or "")
            subcategory = c2.text_input("Subcategory", rec.get("subcategory") or "")
            impact = st.selectbox("Business impact", IMPACT_ORDER, index=IMPACT_ORDER.index(rec.get("business_impact")) if rec.get("business_impact") in IMPACT_ORDER else 0)
            status = st.selectbox("Legislative status", STATUSES, index=STATUSES.index(rec.get("legislative_status")) if rec.get("legislative_status") in STATUSES else len(STATUSES) - 1)
            key_changes = st.text_area("What changed", rec.get("key_changes") or "", height=90)
            obligations = st.text_area("Key obligations", rec.get("key_obligations") or "", height=90)
            follow = st.text_area("Recommended follow-up", rec.get("recommended_follow_up") or "", height=90)
            notes = st.text_area("Internal notes", rec.get("user_notes") or "", height=90)
            deadline = st.text_input("Compliance deadline (YYYY-MM-DD or blank)", rec.get("compliance_deadline") or "")
            if st.form_submit_button("Save edits", type="primary"):
                rec.update({
                    "compliance_domain": domain, "category": category, "subcategory": subcategory,
                    "business_impact": impact, "legislative_status": status, "key_changes": key_changes,
                    "key_obligations": obligations, "recommended_follow_up": follow,
                    "user_notes": notes, "compliance_deadline": deadline,
                })
                upsert_finding(rec, change_type="manual-detail")
                st.success("Saved with history.")
                st.rerun()

        st.divider()
        st.markdown("#### AI-generated analysis")
        st.caption("Uses only this record's structured evidence. Informational only; not legal or tax advice.")
        if rec.get("ai_analysis"):
            st.markdown(rec["ai_analysis"])
        if st.button("Generate / refresh AI analysis", type="primary"):
            try:
                with st.spinner("Generating grounded analysis…"):
                    ai = analyze_finding(rec)
                rec["ai_analysis"] = ai
                upsert_finding(rec, change_type="ai-generated")
                st.rerun()
            except Exception as e:
                st.warning(f"AI analysis is unavailable: {e}")

    with history:
        h = versions(finding_id)
        st.dataframe(h, use_container_width=True, hide_index=True) if not h.empty else st.caption("No changes recorded yet.")


def sources_page():
    st.markdown("### Sources")
    st.caption(f"The application automatically searches registered official sources and discovers new candidate sources. Automatic monitoring runs when due (default every {AUTO_WEB_DISCOVERY_INTERVAL_MINUTES} minutes). You can also add sources manually.")

    diagnostics = search_diagnostics()
    d1, d2, d3 = st.columns(3)
    d1.metric("Search provider", diagnostics.get("provider", "Unavailable"))
    d2.metric("Tavily key", "Detected" if diagnostics.get("tavily_configured") else "Not detected")
    d3.metric("Last web findings", diagnostics.get("last_findings", 0))
    if diagnostics.get("last_error"):
        st.warning("Last monitoring issue: " + str(diagnostics.get("last_error")))

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Search the web now", type="primary", use_container_width=True):
            try:
                with st.spinner("Searching official sources and discovering new candidates…"):
                    result = run_live_monitoring(force=True)
                st.success(f"Web monitoring completed. {result.get('ingestion', {}).get('findings', 0)} relevant source pages were stored/updated.")
                refresh()
            except Exception as exc:
                st.error(f"Web monitoring failed: {exc}")
    with b2:
        if st.button("Test Tavily", use_container_width=True, disabled=not diagnostics.get("tavily_configured")):
            with st.spinner("Testing Tavily search…"):
                result = tavily_connection_test()
            if result.get("ok"):
                st.success(f"Tavily is working: {result.get('result_count', 0)} search result(s) returned.")
            else:
                st.error(result.get("error") or "Tavily test failed.")
    with b3:
        if st.button("Check source health", use_container_width=True):
            with st.spinner("Checking configured sources…"):
                try:
                    results = check_all_sources()
                    st.success(f"Checked {len(results)} source(s).")
                except Exception as e:
                    st.error(str(e))
            refresh()

    sources = list_sources()
    if not sources.empty:
        show_cols = ["id", "jurisdiction", "name", "url", "verification_status", "active", "last_success", "error_state", "discovered_automatically"]
        st.dataframe(sources[show_cols], use_container_width=True, hide_index=True)

    candidates = sources[sources["verification_status"] == "pending verification"] if not sources.empty else pd.DataFrame()
    if not candidates.empty:
        with st.expander(f"Review automatically discovered source candidates ({len(candidates)})"):
            candidate_id = st.selectbox("Candidate", candidates["id"].tolist(), format_func=lambda sid: f"{candidates.loc[candidates['id']==sid, 'jurisdiction'].iloc[0]} · {candidates.loc[candidates['id']==sid, 'name'].iloc[0]}")
            row = candidates[candidates["id"] == candidate_id].iloc[0].to_dict()
            st.write(row.get("url"))
            st.caption(row.get("discovery_reason") or "")
            a1, a2 = st.columns(2)
            if a1.button("Approve and activate", key="approve-source"):
                row["verification_status"] = "likely official source"
                row["active"] = True
                row["authority"] = row.get("authority") or "Pending verification"
                upsert_source(row)
                st.success("Approved. It will be included in automatic monitoring.")
                refresh()
            if a2.button("Reject", key="reject-source"):
                row["verification_status"] = "rejected"
                row["active"] = False
                upsert_source(row)
                st.success("Rejected.")
                refresh()

    with st.expander("Add / update a source manually"):
        with st.form("source-form"):
            sid = st.text_input("Source ID")
            jurisdiction = st.text_input("Jurisdiction")
            authority = st.text_input("Authority")
            name = st.text_input("Name")
            url = st.text_input("Official URL")
            stype = st.text_input("Source type")
            language = st.text_input("Language")
            verification = st.selectbox("Verification status", ["verified official source", "likely official source", "pending verification", "rejected"])
            method = st.selectbox("Retrieval method", ["API", "RSS/Atom", "XML", "HTML + web search", "PDF monitoring", "manual/adapter"])
            active = st.checkbox("Monitor automatically", value=True)
            if st.form_submit_button("Save source", type="primary"):
                if not sid or not jurisdiction or not name or not url:
                    st.error("Source ID, jurisdiction, name and URL are required.")
                else:
                    upsert_source({
                        "id": sid, "jurisdiction": jurisdiction, "authority": authority, "name": name,
                        "url": url, "source_type": stype, "language": language,
                        "verification_status": verification, "retrieval_method": method, "active": active,
                        "last_success": None, "last_failure": None, "error_state": None, "last_checked": None,
                        "discovered_automatically": False, "discovery_reason": "Added manually by a user.",
                    })
                    st.success("Source saved and will be monitored automatically when active.")
                    refresh()


def timeline_page(df: pd.DataFrame):
    st.markdown("### Timeline")
    d = deadline_frame(df, horizon_days=730)
    if d.empty:
        st.info("No confirmed upcoming deadlines in this filtered view.")
        return
    fig = px.scatter(
        d, x="compliance_deadline", y="jurisdiction", color="business_impact",
        hover_name="english_title", category_orders={"business_impact": IMPACT_ORDER},
        color_discrete_map={
            "Informational": "#C7B2D3",
            "Low": "#B98CC8",
            "Medium": "#A20B8D",
            "High": "#FFC400",
            "Critical": "#6F075F",
        },
    )
    fig.update_layout(height=max(380, 100 + 40 * d["jurisdiction"].nunique()), margin=dict(l=10, r=10, t=10, b=10))
    brand_plotly(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    st.dataframe(d[["compliance_deadline", "jurisdiction", "english_title", "category", "business_impact", "source_url"]], use_container_width=True, hide_index=True)


header()
run_automatic_monitoring_once()
all_df = list_findings()
df = filters(all_df)

if st.session_state.selected_finding:
    detail(st.session_state.selected_finding)
else:
    page = st.radio("Navigation", ["Overview", "Developments", "Timeline", "Sources"], horizontal=True, label_visibility="collapsed")
    if page == "Overview":
        overview(df)
    elif page == "Developments":
        developments(df)
    elif page == "Timeline":
        timeline_page(df)
    else:
        sources_page()
