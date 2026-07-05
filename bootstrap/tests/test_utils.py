"""
tests/test_utils.py — Unit tests for the utils module.

Tests verify:
  - slugify produces clean, URL-safe output
  - with_retry retries on RetryableError
  - with_retry propagates non-retryable errors immediately
  - deep_get safely traverses nested dicts
  - chunk_list splits correctly
  - stable_id is deterministic
"""

from __future__ import annotations

import pytest

from bootstrap.utils import (
    RetryableError,
    chunk_list,
    deep_get,
    slugify,
    stable_id,
    utc_date,
    with_retry,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("ADR-001: Use PostgreSQL") == "adr-001-use-postgresql"

    def test_unicode(self):
        # ASCII-only output expected
        result = slugify("Café au lait")
        assert "caf" in result

    def test_multiple_spaces(self):
        assert slugify("a   b   c") == "a-b-c"

    def test_leading_trailing(self):
        assert slugify("  hello  ") == "hello"

    def test_already_slugified(self):
        assert slugify("already-slugified") == "already-slugified"


class TestDeepGet:
    def test_simple(self):
        assert deep_get({"a": 1}, "a") == 1

    def test_nested(self):
        assert deep_get({"a": {"b": {"c": 42}}}, "a", "b", "c") == 42

    def test_missing_key(self):
        assert deep_get({"a": 1}, "b") is None

    def test_missing_nested(self):
        assert deep_get({"a": {"b": 1}}, "a", "c") is None

    def test_default(self):
        assert deep_get({}, "x", default="fallback") == "fallback"

    def test_non_dict_intermediate(self):
        assert deep_get({"a": "string"}, "a", "b") is None


class TestChunkList:
    def test_even_chunks(self):
        result = chunk_list([1, 2, 3, 4], 2)
        assert result == [[1, 2], [3, 4]]

    def test_uneven_chunks(self):
        result = chunk_list([1, 2, 3, 4, 5], 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_larger_than_list(self):
        result = chunk_list([1, 2], 10)
        assert result == [[1, 2]]

    def test_empty_list(self):
        assert chunk_list([], 5) == []


class TestStableId:
    def test_deterministic(self):
        id1 = stable_id("confluence_page", "Home")
        id2 = stable_id("confluence_page", "Home")
        assert id1 == id2

    def test_different_inputs(self):
        id1 = stable_id("confluence_page", "Home")
        id2 = stable_id("confluence_page", "Backend")
        assert id1 != id2

    def test_length(self):
        assert len(stable_id("ns", "key")) == 8


class TestWithRetry:
    def test_success_on_first_try(self):
        calls = []

        @with_retry(max_retries=3, backoff_base=0)
        def fn():
            calls.append(1)
            return "ok"

        result = fn()
        assert result == "ok"
        assert len(calls) == 1

    def test_retries_on_retryable_error(self):
        calls = []

        @with_retry(max_retries=3, backoff_base=0)
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise RetryableError("transient")
            return "ok"

        result = fn()
        assert result == "ok"
        assert len(calls) == 3

    def test_raises_after_max_retries(self):
        @with_retry(max_retries=2, backoff_base=0)
        def fn():
            raise RetryableError("always fails")

        with pytest.raises(RetryableError):
            fn()

    def test_non_retryable_propagates_immediately(self):
        calls = []

        @with_retry(max_retries=5, backoff_base=0)
        def fn():
            calls.append(1)
            raise ValueError("non-retryable")

        with pytest.raises(ValueError):
            fn()
        # Should have only called once
        assert len(calls) == 1


class TestUtcDate:
    def test_format(self):
        date = utc_date()
        # Should be YYYY-MM-DD
        assert len(date) == 10
        assert date[4] == "-"
        assert date[7] == "-"
