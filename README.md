<img src="blob:https://gemini.google.com/b076adf8-3265-458a-b7b7-fb82be43dcbe" alt=""/><img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/13daa8a1-ba92-43af-b6b0-03a8b3287d49" />

# Multi-AI Research Digest

**Single-call structured research pipeline: Streamlit + Google GenAI SDK + Pydantic v2, producing schema-validated technical reports through a deterministic JSON contract.**

![CI Pipeline](https://github.com/Ali-datasmith/multi-ai-research-digest/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.61-FF4B4B?logo=streamlit&logoColor=white)
![Google GenAI](https://img.shields.io/badge/Google-GenAI%20SDK-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)


---

# Demo Video
<video src="https://github.com/user-attachments/assets/93090585-8d08-4b21-839f-5ecdc7d39378" controls width="100%"></video>
---

# Architecture

One inference request per execution. The model emits a fully structured JSON document, parsed natively into a Pydantic object before touching the UI.

```
User Query
     │
     ▼
ResearchEngine  (cached, one HTTP client per server session)
     │
     ▼
Google GenAI SDK  (response_schema = ResearchReport)
     │
     ▼
Native Pydantic Parsing  →  ResearchResult (report + latency + sources)
     │
     ▼
Streamlit Session State  (single-path execution guard)
     │
     ▼
State-Driven UI Rendering
```

- Exactly **one** network request per research execution — no prompt chaining, no JSON stitching.
- Schema-first validation: unparsable payloads terminate before UI rendering.
- Execution ownership lives in a single `research_active` guard, making Streamlit reruns deterministic and duplicate API calls impossible.
- Status-code-first error taxonomy; failures render as categorized operational messages, never raw stack traces.
- Per-run telemetry (model, latency, sources) via `loguru` server-side and a metrics row client-side.

## Single-Path Guard Pattern

```python
if st.session_state.research_active:
    ...   # the only code path allowed to touch the network
```

```
Button Click → research_active=True → single execution path → validated response
             → research_active=False → st.rerun() → state-driven rendering
```

## Structured Response Schema

| Model | Fields |
|--------|--------|
| `ExecutiveSummary` | `high_level_synthesis`, `performance_breakdown` |
| `CodeBoilerplate` | `language`, `snippet`, `explanation` |
| `ProductionRisk` | `title`, `description` |
| `ResearchReport` | `executive_summary`, `code_boilerplate`, `production_risks` |

`language` is schema-enforced and drives syntax highlighting (alias-normalized, with a safe-lexer fallback). Native SDK parsing:

```python
response_schema=ResearchReport
response_mime_type="application/json"
```

## State Management Contract

`st.session_state` is treated as a backend data contract, not ad-hoc UI storage.

| Key | Type | Purpose |
|------|------|---------|
| `research_active` | `bool` | Owns the execution lifecycle; sole owner of network invocation |
| `raw_query` | `str` | Canonical query submitted to the engine |
| `report_data` | `dict \| None` | Validated structured report |
| `error_message` | `str \| None` | Categorized user-facing error |
| `run_meta` | `dict \| None` | Telemetry: model ID, latency, sources |
| `query_input_widget` | `str` | Text-area synchronization across reruns |

Rules: widgets never render from raw API responses; tabs consume persisted state only; the text area is the sole writer of `raw_query`; success and failure both reset the guard before rerun.

## Error Taxonomy

Classification priority: typed validation errors → HTTP status code (`match` on `429 / 401 / 403 / 5xx`) → exception type → substring heuristics (documented last resort for non-SDK exceptions).

| Category | Signal |
|----------|--------|
| **API Quota Exhaustion** | HTTP 429 / `"quota"` |
| **Authentication Error** | HTTP 401/403 / key errors |
| **Network Timeout / Server Unavailable** | HTTP 5xx, `TimeoutError`, `ConnectionError` |
| **Schema Validation Failure** | Pydantic / parse errors |
| **Unexpected System Error** | Fallback catch-all |

On every failure: categorized message stored, stale report cleared, guard reset, consistent rerun.

---

# Testing & CI

22 deterministic tests, fully mocked at the SDK boundary — no network, no API keys, no quota consumption.

```bash
pip install -r requirements-dev.txt
pytest tests/          # 22 passed
```

Coverage: schema contract (required-field enforcement, round-trip), language normalization & lexer fallback, engine lifecycle (secrets → env → default resolution), single-call request shape (exactly one `generate_content`, no tools), parse-failure path, and the full error taxonomy against typed `ClientError`/`ServerError` status codes.

Every push and PR to `main` runs `.github/workflows/ci.yml` (ubuntu-latest, Python 3.11): installs both requirement sets and executes the suite. The badge above reflects the latest run.

---

# UI Theme

Modern Dark Minimalist (Linear/Vercel-grade), committed in `.streamlit/config.toml` plus a presentation-only CSS layer:

- Base `#0B0F19` · surfaces `#121620` · text `#FFFFFF`
- Electric cyan `#00E5FF` reserved for primary action, key metrics, active tab
- Glassmorphic cards: `rgba(255,255,255,0.03)` + 12px blur + 1px hairline borders, no heavy shadows

---

# Repository Layout

```
multi-ai-research-digest/
├── .github/workflows/ci.yml   # CI: install + pytest on push/PR
├── .streamlit/config.toml     # committed theme
├── tests/
│   ├── __init__.py
│   ├── test_error_handling.py # error taxonomy (typed status codes)
│   └── test_research_engine.py# schema, language, engine, telemetry
├── app.py                     # state-driven presentation layer
├── research_engine.py         # single-call synthesis engine
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .gitignore
└── README.md
```

---

# Installation

```bash
git clone https://github.com/Ali-datasmith/multi-ai-research-digest.git
cd multi-ai-research-digest
pip install -r requirements.txt
export GOOGLE_API_KEY="your_api_key"
export GEMINI_MODEL="gemini-3.5-flash"
streamlit run app.py
```

**Streamlit Community Cloud:** credentials go in **Advanced Settings → Secrets** (never in the repo):

```toml
GOOGLE_API_KEY = "your_api_key_here"
GEMINI_MODEL = "gemini-3.5-flash"
```

---

# Design Principles

- Single inference request per execution
- Deterministic state transitions; explicit execution ownership
- Schema-first response validation
- UI rendered exclusively from persisted application state
- Status-code-first, human-readable error classification
- Cached engine: one HTTP client per server session
- Presentation-layer theming with zero impact on the execution path

# Known Limitations

- **No retrieval grounding, by design.** Google Search grounding was excluded because it draws from a separate, tightly capped free-tier quota pool; synthesis relies on the model's parametric knowledge. Treat output as an architectural starting point, not a cited source.
- **Stateless by design.** Each execution is an independent deterministic digest; multi-turn memory is intentionally out of scope.
- **Residual heuristic fallback.** Exceptions carrying no HTTP status code are classified by substring heuristics as a documented last resort.
