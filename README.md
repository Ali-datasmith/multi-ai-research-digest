# Multi-AI Research Digest Streamlit App

**Single-call structured research pipeline that combines Streamlit, the Google GenAI SDK, and Pydantic v2 to produce schema-validated technical reports through a deterministic JSON contract.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Google GenAI](https://img.shields.io/badge/Google-GenAI%20SDK-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

# Architecture

The application is intentionally designed around a **single inference request**. Rather than chaining multiple prompts together, the model produces a fully structured JSON document that is parsed directly into a Pydantic object before being exposed to the UI.

## Single-Call Structured JSON Pipeline

```
User Query
     │
     ▼
ResearchEngine
     │
     ▼
Google GenAI SDK
(response_schema = ResearchReport)
     │
     ▼
Native Pydantic Parsing
     │
     ▼
Validated Python Dictionary
     │
     ▼
Streamlit Session State
     │
     ▼
State-Driven UI Rendering
```

Unlike sequential prompt pipelines, this architecture:

- performs exactly **one network request** per research execution
- eliminates intermediate prompt synchronization
- removes downstream JSON stitching logic
- validates the entire response against a strict Pydantic schema before UI rendering
- reduces user-perceived latency by avoiding multi-stage inference workflows

---

# Single-Path Guard Pattern

Streamlit reruns the entire application whenever widget state changes.

Without an execution guard, a single button interaction can accidentally trigger duplicate API requests during reruns.

This project prevents that by placing the complete network execution path behind a single state flag:

```python
if st.session_state.research_active:
    ...
```

Execution ownership belongs exclusively to `research_active`.

Lifecycle:

```
Button Click
      │
      ▼
research_active = True
      │
      ▼
Single execution path
      │
      ▼
API request
      │
      ▼
Validated response
      │
      ▼
research_active = False
      │
      ▼
st.rerun()
```

This guard ensures:

- exactly one active inference request
- deterministic rerun behavior
- no duplicate concurrent API calls
- state-driven rendering after network completion
- clear separation between execution logic and presentation logic

---

# State Management Contract

The application treats `st.session_state` as a backend data contract rather than ad-hoc UI storage.

| Key | Type | Purpose | Initialization Rule |
|------|------|---------|---------------------|
| `research_active` | `bool` | Owns the execution lifecycle and guards API invocation | Initialized once at application startup |
| `raw_query` | `str` | Canonical research query submitted to the engine | Initialized to empty string |
| `report_data` | `dict \| None` | Stores the validated structured research report | Initialized to `None` |
| `error_message` | `str \| None` | Stores categorized user-facing error messages | Initialized to `None` |
| `query_input_widget` | `str` | Synchronizes the `text_area` widget across reruns | Created automatically by the widget key |

Execution rules:

- widgets never render directly from API responses
- tabs consume only persisted session state
- the text area is the sole writer of `raw_query`
- successful execution always clears execution state before rerunning
- failed execution always resets execution state before rendering errors

---

# Structured Response Schema

The inference output is validated against a nested Pydantic model before entering the application state.

| Model | Fields |
|--------|--------|
| `ExecutiveSummary` | `high_level_synthesis`, `performance_breakdown` |
| `CodeBoilerplate` | `snippet`, `explanation` |
| `ProductionRisk` | `title`, `description` |
| `ResearchReport` | `executive_summary`, `code_boilerplate`, `production_risks` |

The Google GenAI SDK performs native object parsing using:

```python
response_schema=ResearchReport
response_mime_type="application/json"
```

If parsing fails, execution terminates before UI rendering.

---

# Technology Stack

| Component | Responsibility |
|-----------|----------------|
| **Streamlit** | UI composition, execution lifecycle, session state orchestration |
| **google-genai SDK** | Native Gemini client with direct Pydantic object parsing (does **not** use the legacy `google-generativeai` package) |
| **Pydantic v2** | Runtime schema enforcement and structured response validation |
| **Rich** | Server-side terminal telemetry for initialization and execution events |

---

# Repository Layout

```
multi-ai-research-digest/
│
├── app.py
├── research_engine.py
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/<username>/multi-ai-research-digest.git

cd multi-ai-research-digest
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
export GOOGLE_API_KEY="your_api_key"
export GEMINI_MODEL="gemini-3.5-flash"
```

Run the application:

```bash
streamlit run app.py
```

---

# Runtime Flow

```
User Input
     │
     ▼
Session State Update
     │
     ▼
research_active = True
     │
     ▼
ResearchEngine
     │
     ▼
Gemini API
     │
     ▼
Pydantic Validation
     │
     ▼
model_dump()
     │
     ▼
Session State
     │
     ▼
UI Tabs
```

---

# Live Production Telemetry & Error Handling

Failures are classified into explicit operational categories rather than displayed as a generic exception.

| Failure Category | Detection Strategy | User-Facing Message |
|------------------|-------------------|---------------------|
| API Quota Exhaustion | HTTP 429 or `"quota"` | **API Quota Exhaustion** |
| Network Timeout | Timeout, deadline, or HTTP 504 | **Network Timeout / Server Unavailable** |
| Schema Validation Failure | Pydantic, schema, validation errors | **Schema Validation Failure** |
| Authentication Failure | API key, auth, HTTP 401/403 | **Authentication Error** |
| Unexpected Exception | Fallback catch-all | **Unexpected System Error** |

On every failure the application:

- stores a categorized message in `error_message`
- clears any stale report data
- resets the execution guard
- reruns into a consistent UI state

---

# Design Principles

- Single inference request per execution
- Deterministic state transitions
- Schema-first response validation
- UI rendered exclusively from persisted application state
- Explicit execution ownership through a single state guard
- Human-readable operational error classification
- Native structured parsing using the Google GenAI SDK and Pydantic v2