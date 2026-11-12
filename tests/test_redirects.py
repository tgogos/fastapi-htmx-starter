"""Unit checks for safe in-app redirect targets."""

from __future__ import annotations

import pytest

from app.web.redirects import safe_relative_path

pytestmark = pytest.mark.no_client


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/ui/books", "/ui/books"),
        ("/ui/books/search?page=2", "/ui/books/search?page=2"),
        ("https://evil.example/", "/fallback"),
        ("//evil.example/phish", "/fallback"),
        ("\\/\\/evil.example/phish", "/fallback"),
        ("https:/evil.example", "/fallback"),
        ("", "/fallback"),
        ("ui/relative", "/fallback"),
    ],
)
def test_safe_relative_path(value: str, expected: str):
    assert safe_relative_path(value, fallback="/fallback") == expected
