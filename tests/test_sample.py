
# Sample test file - intentionally failing for CI/CD healing demonstration
import pytest

def test_sample_failing():
    """This test intentionally fails to demonstrate CI healing."""
    assert False, "Sample failure - fix this test"

def test_another_failing():
    """Another failing test."""
    result = 1 + 1
    assert result == 3, "Math error - fix this"
