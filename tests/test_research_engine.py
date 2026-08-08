"""Schema contract, language handling, engine lifecycle, and telemetry tests."""

import os
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors
from pydantic import ValidationError

from research_engine import (
    CodeBoilerplate,
    ExecutiveSummary,
    ResearchEngine,
    ResearchResult,
    SchemaValidationError,
    lexer_for,
    normalize_language,
)


def _dummy_report():
    from research_engine import ResearchReport

    return ResearchReport(
        executive_summary={"high_level_synthesis": "s", "performance_breakdown": "p"},
        code_boilerplate={"language": "rust", "snippet": "fn main() {}", "explanation": "e"},
        production_risks=[{"title": "t", "description": "d"}],
    )


def _mock_response():
    response = MagicMock()
    response.parsed = _dummy_report()
    chunk = MagicMock()
    chunk.web.uri = "https://source.dev/a"
    metadata = MagicMock()
    metadata.grounding_chunks = [chunk]
    candidate = MagicMock()
    candidate.grounding_metadata = metadata
    response.candidates = [candidate]
    return response


@pytest.fixture
def mock_client():
    with patch("research_engine.genai.Client") as client_cls:
        instance = MagicMock()
        client_cls.return_value = instance
        yield instance


# --- Schema contract ---

def test_executive_summary_valid():
    obj = ExecutiveSummary(high_level_synthesis="syn", performance_breakdown="perf")
    assert obj.high_level_synthesis == "syn"


def test_code_boilerplate_requires_language():
    with pytest.raises(ValidationError):
        CodeBoilerplate(snippet="x", explanation="y")


def test_report_roundtrip():
    dump = _dummy_report().model_dump()
    assert dump["code_boilerplate"]["language"] == "rust"
    assert len(dump["production_risks"]) == 1


# --- Language handling ---

def test_normalize_language_aliases():
    assert normalize_language("Py") == "python"
    assert normalize_language("GoLang") == "go"
    assert normalize_language("  Rust ") == "rust"


def test_lexer_for_unknown_falls_back_to_text():
    assert lexer_for("python") == "python"
    assert lexer_for("kotlin") == "text"


# --- Engine lifecycle ---

def test_engine_model_from_env(mock_client):
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test-model"}, clear=True):
        assert ResearchEngine().model_id == "gemini-test-model"


def test_engine_model_default(mock_client):
    with patch.dict(os.environ, {}, clear=True):
        assert ResearchEngine().model_id == "gemini-3.5-flash"


def test_execute_returns_verified_result(mock_client):
    mock_client.models.generate_content.return_value = _mock_response()
    result = ResearchEngine().execute_research("Polars vs DuckDB")

    assert isinstance(result, ResearchResult)
    assert isinstance(result.report, dict)
    assert "executive_summary" in result.report
    assert result.sources == ["https://source.dev/a"]
    assert result.elapsed_seconds >= 0
    mock_client.models.generate_content.assert_called_once()


def test_execute_parse_failure_raises_schema_error(mock_client):
    mock_client.models.generate_content.return_value.parsed = None
    with pytest.raises(SchemaValidationError):
        ResearchEngine().execute_research("q")


def test_grounding_degrades_on_400(mock_client):
    rejection = genai_errors.ClientError(
        400, {"error": {"message": "Tool google_search is not supported with response_schema"}}
    )
    mock_client.models.generate_content.side_effect = [rejection, _mock_response()]

    result = ResearchEngine().execute_research("q")

    assert mock_client.models.generate_content.call_count == 2
    assert isinstance(result.report, dict)
