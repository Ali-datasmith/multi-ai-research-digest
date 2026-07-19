import streamlit as st
import os
from research_engine import ResearchEngine

# --- 1. Absolute Top-Level State Initialization ---
# Must be initialized before ANY widget logic or rendering runs.
if "research_active" not in st.session_state:
    st.session_state.research_active = False
if "raw_query" not in st.session_state:
    st.session_state.raw_query = ""
if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None

st.set_page_config(page_title="Multi-AI Research Digest", layout="wide", page_icon="🔬")
st.title("🔬 Multi-AI Research Digest")
st.caption("Phase 1: Single-Call Structured Synthesis Engine")

# --- 2. SINGLE-PATH GUARD ---
# Execution triggers ONLY if research_active is True. Prevents duplicate concurrent calls.
if st.session_state.research_active:
    with st.status(f"Executing Research: {st.session_state.raw_query}", expanded=True) as status:
        try:
            st.write("Initializing Research Engine...")
            engine = ResearchEngine()
            
            st.write("Executing single-call structured extraction...")
            report = engine.execute_research(st.session_state.raw_query)
            
            # Validate conceptual schema (Pydantic handles structural validation in the engine)
            if not isinstance(report, dict) or "executive_summary" not in report:
                raise ValueError("Schema Validation Failure: Returned JSON missing top-level keys.")
                
            st.session_state.report_data = report
            st.session_state.research_active = False
            st.session_state.error_message = None
            status.update(label="Research Complete!", state="complete", expanded=False)
            st.rerun()
            
        except Exception as e:
            err_str = str(e)
            err_type = type(e).__name__
            
            # Distinct, category-labeled error mapping
            if "quota" in err_str.lower() or "429" in err_str:
                msg = f"API Quota Exhaustion: {err_str}"
            elif "timeout" in err_str.lower() or "504" in err_str or "deadline" in err_str.lower():
                msg = f"Network Timeout / Server Unavailable: {err_str}"
            elif "validation" in err_str.lower() or "schema" in err_str.lower() or "pydantic" in err_str.lower():
                msg = f"Schema Validation Failure: AI returned malformed JSON. {err_str}"
            elif "api_key" in err_str.lower() or "auth" in err_str.lower() or "401" in err_str or "403" in err_str:
                msg = f"Authentication Error: Invalid or missing GOOGLE_API_KEY. {err_str}"
            else:
                msg = f"Unexpected System Error ({err_type}): {err_str}"
                
            st.session_state.error_message = msg
            st.session_state.report_data = None
            st.session_state.research_active = False
            status.update(label="Research Failed!", state="error", expanded=True)
            st.rerun()

# --- 3. UI Rendering (Purely state-driven) ---

st.subheader("1. Research Query")
example_queries = [
    "Polars vs DuckDB 2026 memory scaling",
    "Rust vs Go for high-throughput websocket servers",
    "PyTorch 2.5 compile times vs JAX tracing overhead"
]

cols = st.columns(len(example_queries))
for i, ex_q in enumerate(example_queries):
    if cols[i].button(ex_q, use_container_width=True):
        st.session_state.raw_query = ex_q
        st.session_state.query_input_widget = ex_q  # Sync widget state
        st.session_state.report_data = None
        st.session_state.error_message = None
        st.session_state.research_active = True
        st.rerun()

# We use a key for the text_area to preserve user typing across Streamlit reruns 
# (e.g. if they interact with an expander before hitting submit).
query_input = st.text_area(
    "Enter your technical query:",
    value=st.session_state.raw_query,
    height=100,
    placeholder="e.g., Polars vs DuckDB 2026 memory scaling",
    key="query_input_widget"
)

if st.button("Execute Research", type="primary", disabled=st.session_state.research_active):
    current_input = st.session_state.get("query_input_widget", "").strip()
    if current_input:
        # The widget is the ONLY place allowed to write to raw_query
        st.session_state.raw_query = current_input
        st.session_state.report_data = None
        st.session_state.error_message = None
        st.session_state.research_active = True
        st.rerun()
    else:
        st.warning("Please enter a valid query before executing.")

# Error display block
if st.session_state.error_message:
    st.error(st.session_state.error_message)

# Output Interface
if st.session_state.report_data:
    st.subheader("2. Research Digest")
    report = st.session_state.report_data
    
    # Tabs read purely from pre-existing state data.
    tab1, tab2, tab3 = st.tabs([
        "📊 Executive Summary & Performance", 
        "💻 Code Implementation Boilerplate", 
        "⚠️ Discovered Production Risks"
    ])
    
    with tab1:
        st.markdown("### High-Level Synthesis")
        st.markdown(report["executive_summary"].get("high_level_synthesis", "No synthesis provided."))
        st.markdown("### Performance Breakdown")
        st.markdown(report["executive_summary"].get("performance_breakdown", "No breakdown provided."))
        
    with tab2:
        lang = report["code_boilerplate"].get("language", "python")
        st.markdown(f"### Language: `{lang}`")
        st.code(report["code_boilerplate"].get("snippet", "# No snippet generated"), language=lang.lower())
        st.info(report["code_boilerplate"].get("explanation", ""))
        
    with tab3:
        st.markdown("### Edge Cases & Risks")
        risks = report.get("production_risks", [])
        if not risks:
            st.info("No specific production risks identified by the model.")
        else:
            for risk in risks:
                with st.expander(f"⚠️ {risk.get('title', 'Unnamed Risk')}"):
                    st.markdown(risk.get("description", ""))
