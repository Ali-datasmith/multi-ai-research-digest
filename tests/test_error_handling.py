import pytest

def categorize_error(err_str: str, err_type: str) -> str:
    """Replicates the exact error mapping logic from app.py for isolated testing."""
    if "quota" in err_str.lower() or "429" in err_str:
        return f"API Quota Exhaustion: {err_str}"
    elif "timeout" in err_str.lower() or "504" in err_str or "deadline" in err_str.lower():
        return f"Network Timeout / Server Unavailable: {err_str}"
    elif "validation" in err_str.lower() or "schema" in err_str.lower() or "pydantic" in err_str.lower():
        return f"Schema Validation Failure: AI returned malformed JSON. {err_str}"
    elif "api_key" in err_str.lower() or "auth" in err_str.lower() or "401" in err_str or "403" in err_str:
        return f"Authentication Error: Invalid or missing GOOGLE_API_KEY. {err_str}"
    else:
        return f"Unexpected System Error ({err_type}): {err_str}"

def test_error_quota():
    assert categorize_error("Exceeded quota 429", "Exception").startswith("API Quota Exhaustion")

def test_error_timeout():
    assert categorize_error("Deadline exceeded", "TimeoutError").startswith("Network Timeout")

def test_error_validation():
    assert categorize_error("Pydantic schema validation failed", "ValidationError").startswith("Schema Validation Failure")

def test_error_auth():
    assert categorize_error("Invalid API_KEY provided", "AuthError").startswith("Authentication Error")

def test_error_unknown():
    assert categorize_error("Unknown bug", "RuntimeError").startswith("Unexpected System Error")
