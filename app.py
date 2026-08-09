"""Multi-AI Research Digest — Streamlit presentation layer.

The UI is purely state-driven. Execution ownership belongs exclusively to
the `research_active` guard (Single-Path Guard Pattern).
"""

import streamlit as st
from loguru import logger

from research_engine import (
    ResearchEngine,
    SchemaValidationError,
    classify_error,
    lexer_for,
    normalize_language,
)

# --- 1. Absolute top-level state initialization ----------------------------
if "research_active" not in st.session_state:
    st.session_state.research_active = False
if "raw_query" not in st.session_state:
    st.session_state.raw_query = ""
if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "run_meta" not in st.session_state:
    st.session_state.run_meta = None

st.set_page_config(page_title="Multi-AI Research Digest", layout="wide")

# --- Theme injection V1 (presentational only — zero impact on execution path) ---
st.markdown(
    """
<style>
/* Base canvas: deep charcoal */
.stApp { background-color: #0B0F19; }

/* Typography: pure white headers, muted silver body */
h1, h2, h3, h4 { color: #FFFFFF !important; letter-spacing: -0.01em; }
.stMarkdown p, .stMarkdown li, label, div[data-testid="stCaptionContainer"] { color: #8E8E93; }
div[data-testid="stAlert"] p, div[data-testid="stAlert"] li { color: inherit !important; }

/* Glassmorphic surfaces: 3% white + 12px blur + 1px crisp border, no heavy shadows */
div[data-testid="stExpander"] details,
div[data-testid="stMetric"],
div[data-testid="stCodeBlock"],
div[data-testid="stTextArea"] > div > div,
div[data-testid="stSidebarContent"] {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    box-shadow: none !important;
}

/* Electric cyan accent — sparingly: primary action, key metrics, active tab, links */
button[data-testid="stBaseButton-primary"] {
    background: #00E5FF !important;
    color: #0B0F19 !important;
    border: 1px solid rgba(0, 229, 255, 0.35);
    font-weight: 600;
}
div[data-testid="stMetricValue"] { color: #00E5FF !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #00E5FF !important;
    border-bottom: 2px solid #00E5FF !important;
}
a { color: #00E5FF; }

/* Hairline dividers instead of shadows */
hr { border-color: rgba(255, 255, 255, 0.08) !important; }
</style>
""",
    unsafe_allow_html=True,
)



@st.cache_resource
def get_engine() -> ResearchEngine:
    """Cached engine: the HTTP client is built once per server session."""
    return ResearchEngine()


# --- 2. SINGLE-PATH GUARD ----------------------------------------------------
if st.session_state.research_active:
    with st.status(f"Executing research: {st.session_state.raw_query}", expanded=True) as status:
        try:
            st.write("Initializing research engine...")
            engine = get_engine()

            st.write("Executing single-call structured extraction...")
            result = engine.execute_research(st.session_state.raw_query)

            if not isinstance(result.report, dict) or "executive_summary" not in result.report:
                raise SchemaValidationError("Returned JSON missing top-level keys.")

            st.session_state.report_data = result.report
            st.session_state.run_meta = {
                "model": result.model_id,
                "latency": result.elapsed_seconds,
                "sources": result.sources,
            }
            st.session_state.research_active = False
            st.session_state.error_message = None
            status.update(label="Research complete", state="complete", expanded=False)
            st.rerun()

        except Exception as exc:  # boundary layer: categorize, never crash
            category, detail = classify_error(exc)
            logger.error(f"{category}: {detail}")
            st.session_state.error_message = f"{category}: {detail}"
            st.session_state.report_data = None
            st.session_state.run_meta = None
            st.session_state.research_active = False
            status.update(label="Research failed", state="error", expanded=True)
            st.rerun()

# --- 3. Header ----------------------------------------------------------------
st.title("Multi-AI Research Digest")
st.caption("Single-call structured synthesis · schema-validated output · Google GenAI SDK + Pydantic v2")

# --- 4. Query input --------------------------------------------------------------
st.subheader("Research Query")

example_queries = [
    "Polars vs DuckDB 2026 memory scaling",
    "Rust vs Go for high-throughput websocket servers",
    "PyTorch 2.5 compile times vs JAX tracing overhead",
]
cols = st.columns(len(example_queries))
for i, example in enumerate(example_queries):
    if cols[i].button(example, use_container_width=True):
        st.session_state.raw_query = example
        st.session_state.query_input_widget = example
        st.session_state.report_data = None
        st.session_state.error_message = None
        st.session_state.research_active = True
        st.rerun()

st.text_area(
    "Enter your technical query:",
    height=100,
    placeholder="e.g. Polars vs DuckDB 2026 memory scaling",
    key="query_input_widget",
)

if st.button("Execute Research", type="primary", disabled=st.session_state.research_active):
    current_input = st.session_state.get("query_input_widget", "").strip()
    if current_input:
        st.session_state.raw_query = current_input
        st.session_state.report_data = None
        st.session_state.error_message = None
        st.session_state.research_active = True
        st.rerun()
    else:
        st.warning("Please enter a valid query before executing.")

if st.session_state.error_message:
    st.error(st.session_state.error_message)

# --- 5. State-driven output --------------------------------------------------------
if st.session_state.report_data:
    report = st.session_state.report_data
    st.divider()
    st.subheader("Research Digest")

    if st.session_state.run_meta:
        m_model, m_latency, m_sources = st.columns(3)
        m_model.metric("Model", st.session_state.run_meta["model"])
        m_latency.metric("Latency", f"{st.session_state.run_meta['latency']}s")
        m_sources.metric("Grounding sources", len(st.session_state.run_meta["sources"]))

    tab1, tab2, tab3 = st.tabs(["Executive Summary", "Implementation Boilerplate", "Production Risks"])

    with tab1:
        st.markdown("### High-Level Synthesis")
        st.markdown(report["executive_summary"].get("high_level_synthesis", "No synthesis provided."))
        st.markdown("### Performance Breakdown")
        st.markdown(report["executive_summary"].get("performance_breakdown", "No breakdown provided."))
        sources = (st.session_state.run_meta or {}).get("sources", [])
        if sources:
            with st.expander(f"Grounding sources ({len(sources)})"):
                for uri in sources:
                    st.markdown(f"- {uri}")

    with tab2:
        boilerplate = report["code_boilerplate"]
        lang = normalize_language(boilerplate.get("language"))
        st.markdown(f"### Language: `{lang}`")
        st.code(boilerplate.get("snippet", "# No snippet generated"), language=lexer_for(lang))
        st.info(boilerplate.get("explanation", ""))

    with tab3:
        st.markdown("### Edge Cases & Risks")
        risks = report.get("production_risks", [])
        if not risks:
            st.info("No specific production risks identified by the model.")
        else:
            for risk in risks:
                with st.expander(risk.get("title", "Unnamed Risk")):
                    st.markdown(risk.get("description", ""))
