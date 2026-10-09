from __future__ import annotations
import streamlit as st


def apply_branding():
    """Pigment-inspired brand layer that stays readable in light and dark mode."""
    st.markdown(
        """
        <style>
        :root {
            --brand-purple:#A20B8D;
            --brand-purple-deep:#6E075F;
            --brand-purple-bright:#C014A8;
            --brand-yellow:#FFC400;
            --brand-yellow-deep:#E8AE00;
            --ci-bg:var(--background-color);
            --ci-surface:var(--secondary-background-color);
            --ci-text:var(--text-color);
            --ci-border:color-mix(in srgb, var(--text-color) 14%, transparent);
            --ci-muted:color-mix(in srgb, var(--text-color) 64%, transparent);
            --ci-purple-soft:color-mix(in srgb, var(--brand-purple) 10%, var(--background-color));
            --ci-yellow-soft:color-mix(in srgb, var(--brand-yellow) 13%, var(--background-color));
            --ci-shadow:0 10px 28px color-mix(in srgb, #000 8%, transparent);
        }

        /* Page canvas: subtle Pigment-style atmosphere, not a flat sheet. */
        .stApp {
            background:
                radial-gradient(circle at 8% 2%, color-mix(in srgb, var(--brand-purple) 10%, transparent) 0, transparent 24rem),
                radial-gradient(circle at 96% 8%, color-mix(in srgb, var(--brand-yellow) 11%, transparent) 0, transparent 22rem),
                var(--ci-bg);
        }
        [data-testid="stAppViewContainer"] > .main {
            background:transparent;
        }
        .block-container {
            max-width:1440px;
            padding-top:4.35rem;
            padding-bottom:4rem;
        }

        h1,h2,h3,h4 {
            color:var(--ci-text) !important;
            letter-spacing:-0.025em;
        }
        h1 { font-weight:800 !important; }
        h2,h3 { font-weight:720 !important; }
        .muted { color:var(--ci-muted); }

        /* Main masthead. A small yellow rule echoes the client deck. */
        .hero {
            position:relative;
            overflow:hidden;
            padding:1.55rem 1.65rem 1.45rem 1.65rem;
            border:1px solid var(--ci-border);
            border-radius:22px;
            background:
                linear-gradient(115deg,
                    color-mix(in srgb, var(--ci-surface) 96%, var(--brand-purple)) 0%,
                    var(--ci-surface) 60%,
                    color-mix(in srgb, var(--brand-yellow) 11%, var(--ci-surface)) 100%);
            box-shadow:var(--ci-shadow);
            margin-bottom:1.15rem;
        }
        .hero::before {
            content:"";
            position:absolute;
            inset:0 auto 0 0;
            width:6px;
            background:linear-gradient(180deg,var(--brand-purple) 0 68%,var(--brand-yellow) 68% 100%);
        }
        .hero::after {
            content:"";
            position:absolute;
            width:190px;
            height:190px;
            right:-72px;
            top:-108px;
            border-radius:50%;
            border:28px solid color-mix(in srgb, var(--brand-purple) 8%, transparent);
            pointer-events:none;
        }
        .eyebrow {
            color:var(--brand-purple-bright);
            font-weight:800;
            font-size:.79rem;
            line-height:1.35;
            text-transform:uppercase;
            letter-spacing:.11em;
            padding-top:.1rem;
            margin-bottom:.15rem;
        }

        /* Metrics behave like compact executive cards. */
        [data-testid="stMetric"] {
            min-height:104px;
            background:color-mix(in srgb, var(--ci-surface) 96%, transparent);
            color:var(--ci-text);
            border:1px solid var(--ci-border);
            border-radius:17px;
            padding:.92rem 1.05rem;
            box-shadow:0 5px 18px color-mix(in srgb, #000 5%, transparent);
            transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease;
        }
        [data-testid="stMetric"]:hover {
            transform:translateY(-1px);
            border-color:color-mix(in srgb, var(--brand-purple) 42%, var(--ci-border));
            box-shadow:0 9px 24px color-mix(in srgb, #000 8%, transparent);
        }
        [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
            color:var(--ci-muted) !important;
            font-weight:650;
        }
        [data-testid="stMetricValue"] {
            color:var(--brand-purple-bright) !important;
            font-weight:800;
            letter-spacing:-.035em;
        }

        /* Section rhythm. */
        hr {
            border-color:var(--ci-border) !important;
            margin:1.45rem 0 1.35rem 0 !important;
        }
        [data-testid="stCaptionContainer"] { color:var(--ci-muted); }

        /* Navigation becomes a restrained pill bar. */
        div[role="radiogroup"] {
            gap:.42rem !important;
            background:color-mix(in srgb, var(--ci-surface) 88%, transparent);
            border:1px solid var(--ci-border);
            border-radius:999px;
            padding:.28rem .34rem;
            width:max-content;
            max-width:100%;
            margin:.1rem 0 .9rem 0;
        }
        div[role="radiogroup"] label {
            border-radius:999px !important;
            padding:.23rem .55rem !important;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background:var(--ci-purple-soft);
        }
        div[role="radiogroup"] label:has(input:checked) p {
            color:var(--brand-purple-bright) !important;
            font-weight:750 !important;
        }

        /* Inputs and selectors keep a polished, coherent surface. */
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div {
            border-radius:12px !important;
            border-color:var(--ci-border) !important;
        }
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {
            border-color:var(--brand-purple) !important;
            box-shadow:0 0 0 1px var(--brand-purple) !important;
        }

        /* Buttons: purple primary, neutral secondary, gentle rounding. */
        .stButton>button,
        .stDownloadButton>button,
        [data-testid="stLinkButton"] a {
            border-radius:11px !important;
            font-weight:700 !important;
            transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease;
        }
        .stButton>button:hover,
        .stDownloadButton>button:hover,
        [data-testid="stLinkButton"] a:hover {
            transform:translateY(-1px);
        }
        .stButton>button[kind="primary"] {
            background:linear-gradient(135deg,var(--brand-purple),var(--brand-purple-deep)) !important;
            border-color:var(--brand-purple) !important;
            color:#fff !important;
            box-shadow:0 7px 18px color-mix(in srgb, var(--brand-purple) 22%, transparent);
        }

        /* Data surfaces resemble editable Pigment blocks. */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            border:1px solid var(--ci-border);
            border-radius:15px;
            overflow:hidden;
            background:color-mix(in srgb, var(--ci-surface) 96%, transparent);
            box-shadow:0 5px 18px color-mix(in srgb, #000 4%, transparent);
        }
        [data-testid="stPlotlyChart"] {
            border:1px solid var(--ci-border);
            border-radius:16px;
            overflow:hidden;
            background:color-mix(in srgb, var(--ci-surface) 94%, transparent);
            padding:.25rem;
            box-shadow:0 5px 18px color-mix(in srgb, #000 4%, transparent);
        }

        .ai-box {
            border:1px solid color-mix(in srgb, var(--brand-yellow) 46%, var(--ci-border));
            border-left:5px solid var(--brand-yellow);
            background:linear-gradient(110deg,var(--ci-yellow-soft),color-mix(in srgb,var(--ci-surface) 95%,transparent));
            color:var(--ci-text);
            border-radius:13px;
            padding:.95rem 1rem;
        }
        .source-box {
            border:1px solid color-mix(in srgb, var(--brand-purple) 32%, var(--ci-border));
            border-left:5px solid var(--brand-purple);
            background:linear-gradient(110deg,var(--ci-purple-soft),color-mix(in srgb,var(--ci-surface) 95%,transparent));
            color:var(--ci-text);
            border-radius:13px;
            padding:.95rem 1rem;
        }
        .live-pill {
            display:inline-block;
            border:1px solid color-mix(in srgb, var(--brand-purple) 28%, var(--ci-border));
            border-radius:999px;
            background:var(--ci-purple-soft);
            color:var(--brand-purple-bright);
            padding:.28rem .62rem;
            font-size:.72rem;
            font-weight:750;
        }

        /* Sidebar stays understated so the main canvas remains the focus. */
        [data-testid="stSidebar"] {
            background:color-mix(in srgb, var(--ci-surface) 96%, var(--brand-purple) 4%);
            border-right:1px solid var(--ci-border);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            color:var(--brand-purple-bright) !important;
        }
        [data-testid="stAlert"] {
            border-color:var(--ci-border);
            border-radius:13px;
        }
        a { text-underline-offset:2px; }

        /* Tabs and expanders get cleaner framing. */
        [data-testid="stExpander"] {
            border:1px solid var(--ci-border) !important;
            border-radius:14px !important;
            background:color-mix(in srgb, var(--ci-surface) 94%, transparent);
        }
        [data-baseweb="tab-list"] {
            gap:.3rem;
        }
        [data-baseweb="tab"] {
            border-radius:10px 10px 0 0;
            font-weight:650;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --ci-border:color-mix(in srgb, var(--text-color) 22%, transparent);
                --ci-purple-soft:color-mix(in srgb, var(--brand-purple) 18%, var(--background-color));
                --ci-yellow-soft:color-mix(in srgb, var(--brand-yellow) 9%, var(--background-color));
                --ci-shadow:0 12px 30px rgba(0,0,0,.24);
            }
            .stApp {
                background:
                    radial-gradient(circle at 9% 1%, color-mix(in srgb, var(--brand-purple) 14%, transparent) 0, transparent 26rem),
                    radial-gradient(circle at 94% 7%, color-mix(in srgb, var(--brand-yellow) 6%, transparent) 0, transparent 24rem),
                    var(--ci-bg);
            }
        }

        @media (max-width: 900px) {
            .block-container { padding-top:4rem; }
            .hero { padding:1.25rem 1.2rem 1.15rem 1.35rem; border-radius:18px; }
            div[role="radiogroup"] { width:100%; overflow-x:auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
