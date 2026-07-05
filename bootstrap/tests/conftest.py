"""
tests/conftest.py — Shared pytest fixtures for the Engineering OS Bootstrapper tests.
"""

from __future__ import annotations

import pytest

from bootstrap.config import AtlassianConfig
from bootstrap.logger import ExecutionSummary
from bootstrap.renderer import Renderer


@pytest.fixture(scope="session")
def base_cfg() -> AtlassianConfig:
    """A base configuration with dry_run=True for safe testing."""
    return AtlassianConfig(
        atlassian_email="test@example.com",
        atlassian_api_token="test-token",
        atlassian_base_url="https://test.atlassian.net",
        confluence_cloud_id="test-cloud-id",
        confluence_root_space_id="65841",
        confluence_root_space_key="TWC",
        jira_project_key="TEST",
        jira_default_assignee="test-user-id",
        dry_run=True,
        resume=False,
        max_retries=1,
        retry_backoff_base=0.01,
    )


@pytest.fixture
def summary() -> ExecutionSummary:
    """A fresh ExecutionSummary for each test."""
    return ExecutionSummary()


@pytest.fixture(scope="session")
def renderer() -> Renderer:
    """A shared Renderer instance (template loading is read-only)."""
    return Renderer()


@pytest.fixture
def minimal_page_context() -> dict:
    """Minimal context dict that satisfies all templates."""
    return {
        "title": "Test Page",
        "status": "Draft",
        "owner": "Test Owner",
        "last_updated": "2026-07-05",
        "scope": "Test Scope",
        "purpose": "This is a test page.",
        "related_pages": [],
        "related_jira_epics": [],
        "dependencies": [],
        "repository_paths": [],
        "open_questions": [],
        "notes": "",
    }
