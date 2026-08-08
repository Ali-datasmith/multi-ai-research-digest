"""Multi-AI Research Digest — core synthesis engine.

Design contract:
- Exactly one inference request per research execution.
- Schema-locked JSON output via native Pydantic parsing (google-genai SDK).
- Optional Google Search grounding with graceful degradation on models
  that reject the schema + search combination.
- Status-code-first error classification (substring heuristics only as a
  documented last resort).
- Per-run telemetry via loguru: latency and grounding sources.

Python 3.10+.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

DEFAULT_MODEL = "gemini-3.5-flash"

# --- Error taxonomy: single source of truth --------------------------------
CAT_QUOTA = "API Quota Exhaustion"
CAT_TIMEOUT = "Network Timeout / Server Unavailable"
CAT_SCHEMA = "Schema Validation Failure"
CAT_AUTH = "Authentication Error"
CAT_UNEXPECTED = "Unexpected System Error"


class SchemaValidationError(ValueError):
    """Raised when the model payload fails structural validation."""


# --- Structured output schema ----------------------------------------------
class ExecutiveSummary(BaseModel):
    high_level_synthesis: str = Field(description="High-level architectural overview and direct executive comparison.")
    performance_breakdown: str = Field(description="Deep dive into memory overhead, execution metrics, and latency trade-offs.")


class CodeBoilerplate(BaseModel):
    language: str = Field(description="Primary programming language of the snippet (e.g. 'python', 'rust', 'go'). Drives syntax highlighting in the UI.")
    snippet: str = Field(description="Production-ready minimal implementation example showing configuration rules inside standard markdown code blocks.")
    explanation: str = Field(description="Brief explanation of the optimization logic inside the code snippet.")


class ProductionRisk(BaseModel):
    title: str = Field(description="Short descriptive title of the risk or edge case.")
    description: str = Field(description="Detailed architectural mitigation strategy.")


class ResearchReport(BaseModel):
    executive_summary: ExecutiveSummary
    code_boilerplate: CodeBoilerplate
    production_risks: list[ProductionRisk]


@dataclass
class ResearchResult:
    """Verified engine output plus per-run telemetry."""

    report: dict
    model_id: str
    elapsed_seconds: float
    sources: list[str] = field(default_factory=list)


# --- Language handling -------------------------------------------------------
_LANGUAGE_ALIASES = {"py": "python", "golang": "go", "js": "javascript", "ts": "typescript", "rs": "rust", "sh": "bash"}
_KNOWN_LEXERS = {"python", "rust", "go", "javascript", "typescript", "java", "c", "cpp", "bash", "sql", "yaml", "json", "html", "markdown", "text"}


def normalize_language(raw: str | None) -> str:
    lang = (raw or "python").strip().lower()
    return _LANGUAGE_ALIASES.get(lang, lang)


def lexer_for(lang: str) -> str:
    return lang if lang in _KNOWN_LEXERS else "text"


# --- Error classification ------------------------------------------------------
def classify_error(exc: BaseException) -> tuple[str, str]:
    """Map any exception to (category, detail).

    Priority: typed validation errors -> HTTP status code -> exception type ->
    substring heuristics (last resort, for non-SDK exceptions only).
    """
    detail = str(exc) or type(exc).__name__

    if isinstance(exc, (ValidationError, SchemaValidationError)):
        return CAT_SCHEMA, detail

    code = getattr(exc, "code", None)
    if isinstance(code, str) and code.isdigit():
        code = int(code)
    if isinstance(code, int):
        match code:
            case 429:
                return CAT_QUOTA, detail
            case 401 | 403:
                return CAT_AUTH, detail
            case 500 | 502 | 503 | 504:
                return CAT_TIMEOUT, detail

    if isinstance(exc, (TimeoutError, ConnectionError)):
        return CAT_TIMEOUT, detail

    low = detail.lower()
    if "quota" in low or "429" in detail:
        return CAT_QUOTA, detail
    if "timeout" in low or "deadline" in low or "504" in detail:
        return CAT_TIMEOUT, detail
    if "api_key" in low or "auth" in low or "401" in detail or "403" in detail:
        return CAT_AUTH, detail
    if "validation" in low or "schema" in low or "pydantic" in low:
        return CAT_SCHEMA, detail
    return CAT_UNEXPECTED, f"({type(exc).__name__}) {detail}"


def _extract_sources(response) -> list[str]:
    """Best-effort grounding URI extraction. Never raises."""
    uris: list[str] = []
    try:
        metadata = response.candidates[0].grounding_metadata
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            uri = getattr(getattr(chunk, "web", None), "uri", None)
            if uri and uri not in uris:
                uris.append(uri)
    except Exception:
        pass
    return uris


SYSTEM_PROMPT = (
    "You are an elite Staff Data Engineer. Synthesize a highly rigorous technical evaluation "
    "based on the user's query. Provide clean production architectural insights. "
    "Always set code_boilerplate.language to the actual language of the snippet."
)


class ResearchEngine:
    """Single-call structured synthesis client."""

    def __init__(self, enable_grounding: bool = True):
        try:
            import streamlit as st

            self.model_id = st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
        except Exception:
            self.model_id = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

        self.enable_grounding = enable_grounding
        self.client = genai.Client()
        logger.success(f"Research Engine initialized | model={self.model_id} | grounding={self.enable_grounding}")

    def _config(self, grounded: bool) -> types.GenerateContentConfig:
        kwargs = dict(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ResearchReport,
            temperature=0.2,
        )
        if grounded:
            kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        return types.GenerateContentConfig(**kwargs)

    def execute_research(self, query: str) -> ResearchResult:
        """Execute the single-call pipeline and return a verified result."""
        logger.info(f"Query received: '{query}'")

        start = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model_id, contents=query, config=self._config(self.enable_grounding)
            )
        except genai_errors.ClientError as exc:
            # Older models reject schema + search grounding: degrade, never crash.
            if self.enable_grounding and getattr(exc, "code", None) == 400:
                logger.warning("Grounding rejected for this model; retrying schema-only.")
                response = self.client.models.generate_content(
                    model=self.model_id, contents=query, config=self._config(False)
                )
            else:
                logger.error(f"SDK client error: {exc}")
                raise
        elapsed = time.perf_counter() - start

        if response.parsed is None:
            logger.error("Model returned an unparsable payload for the ResearchReport schema.")
            raise SchemaValidationError("Model returned an unparsable payload for the ResearchReport schema.")

        sources = _extract_sources(response)
        logger.success(f"Research complete | latency={elapsed:.2f}s | sources={len(sources)}")

        return ResearchResult(
            report=response.parsed.model_dump(),
            model_id=self.model_id,
            elapsed_seconds=round(elapsed, 2),
            sources=sources,
        )
