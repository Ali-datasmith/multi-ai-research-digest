"""Error taxonomy tests: status-code-first classification with typed SDK errors."""

import pytest
from google.genai import errors as genai_errors
from pydantic import ValidationError

from research_engine import (
    CAT_AUTH,
    CAT_QUOTA,
    CAT_SCHEMA,
    CAT_TIMEOUT,
    CAT_UNEXPECTED,
    CodeBoilerplate,
    SchemaValidationError,
    classify_error,
)


@pytest.mark.parametrize(
    "cls,code,category",
    [
        (genai_errors.ClientError, 429, CAT_QUOTA),
        (genai_errors.ClientError, 401, CAT_AUTH),
        (genai_errors.ClientError, 403, CAT_AUTH),
        (genai_errors.ServerError, 503, CAT_TIMEOUT),
        (genai_errors.ServerError, 504, CAT_TIMEOUT),
    ],
)
def test_status_code_classification(cls, code, category):
    assert classify_error(cls(code, {"error": {"message": "boom"}}))[0] == category


def test_timeout_type():
    assert classify_error(TimeoutError("deadline"))[0] == CAT_TIMEOUT


def test_connection_type():
    assert classify_error(ConnectionError("reset"))[0] == CAT_TIMEOUT


def test_pydantic_validation():
    with pytest.raises(ValidationError) as err:
        CodeBoilerplate(snippet="x", explanation="y")
    assert classify_error(err.value)[0] == CAT_SCHEMA


def test_schema_validation_error():
    assert classify_error(SchemaValidationError("bad payload"))[0] == CAT_SCHEMA


def test_substring_fallback_quota():
    assert classify_error(ValueError("Exceeded quota 429"))[0] == CAT_QUOTA


def test_substring_fallback_auth():
    assert classify_error(ValueError("invalid api_key"))[0] == CAT_AUTH


def test_unexpected_fallback():
    category, detail = classify_error(RuntimeError("boom"))
    assert category == CAT_UNEXPECTED
    assert "RuntimeError" in detail
