import pytest
from unittest.mock import patch, MagicMock
import os
from research_engine import (
    ExecutiveSummary, CodeBoilerplate, ProductionRisk, 
    ResearchReport, ResearchEngine
)
from pydantic import ValidationError

# --- Pydantic Model Tests ---
def test_executive_summary_valid():
    obj = ExecutiveSummary(high_level_synthesis="syn", performance_breakdown="perf")
    assert obj.high_level_synthesis == "syn"

def test_code_boilerplate_missing_field():
    with pytest.raises(ValidationError):
        CodeBoilerplate(snippet="code") # missing explanation

def test_research_report_full_schema():
    report = ResearchReport(
        executive_summary={"high_level_synthesis": "s", "performance_breakdown": "p"},
        code_boilerplate={"snippet": "s", "explanation": "e"},
        production_risks=[{"title": "t", "description": "d"}]
    )
    assert len(report.production_risks) == 1
    assert report.code_boilerplate.snippet == "s"

# --- Engine Tests ---
@pytest.fixture
def mock_genai_response():
    mock_resp = MagicMock()
    dummy_report = ResearchReport(
        executive_summary={"high_level_synthesis": "s", "performance_breakdown": "p"},
        code_boilerplate={"snippet": "s", "explanation": "e"},
        production_risks=[]
    )
    mock_resp.parsed = dummy_report
    return mock_resp

@pytest.fixture
def mock_genai_client(mock_genai_response):
    with patch('research_engine.genai.Client') as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_genai_response
        yield mock_client_instance

def test_engine_initialization_env_var(mock_genai_client):
    # When run in pytest, st.secrets throws an exception, triggering the env var fallback.
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test-model"}, clear=True):
        engine = ResearchEngine()
        assert engine.model_id == "gemini-test-model"

def test_engine_initialization_default(mock_genai_client):
    with patch.dict(os.environ, {}, clear=True):
        engine = ResearchEngine()
        assert engine.model_id == "gemini-3.5-flash"

def test_execute_research_success(mock_genai_client):
    engine = ResearchEngine()
    result = engine.execute_research("Polars vs DuckDB")
    
    assert isinstance(result, dict)
    assert "executive_summary" in result
    assert "code_boilerplate" in result
    mock_genai_client.models.generate_content.assert_called_once()

def test_execute_research_parsing_failure(mock_genai_client):
    # Force parsing to fail
    mock_genai_client.models.generate_content.return_value.parsed = None
    
    engine = ResearchEngine()
    with pytest.raises(ValueError, match="Failed to parse response"):
        engine.execute_research("Query")
