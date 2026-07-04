"""
tests/test_confluence.py — Unit tests for Confluence PageManager.

Tests idempotency (create vs update vs skip), error handling,
template selection, and hierarchy building using mocked clients.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bootstrap.config import AtlassianConfig
from bootstrap.confluence import (
    ConfluenceClient,
    PageManager,
    PageSpec,
    _choose_template,
    _build_context,
)
from bootstrap.logger import ExecutionSummary
from bootstrap.renderer import Renderer


@pytest.fixture
def cfg():
    return AtlassianConfig(
        atlassian_email="test@example.com",
        atlassian_api_token="test-token",
        atlassian_base_url="https://test.atlassian.net",
        confluence_cloud_id="test-cloud",
        confluence_root_space_id="65841",
        confluence_root_space_key="TWC",
        jira_project_key="TEST",
        jira_default_assignee="user-id",
        dry_run=False,
        resume=False,
    )


@pytest.fixture
def dry_cfg(cfg):
    cfg.dry_run = True
    return cfg


@pytest.fixture
def summary():
    return ExecutionSummary()


@pytest.fixture
def renderer():
    return Renderer()


class TestChooseTemplate:
    def test_product_vision_maps_to_product(self):
        assert _choose_template("Product Vision", depth=2) == "product.md"

    def test_architecture_maps_to_architecture(self):
        assert _choose_template("Backend Architecture", depth=3) == "architecture.md"

    def test_adr_maps_to_adr(self):
        assert _choose_template("ADR-001 Decision", depth=3) == "adr.md"

    def test_runbook_maps_to_runbook(self):
        assert _choose_template("Runbook — Deploy", depth=4) == "runbook.md"

    def test_api_maps_to_api(self):
        assert _choose_template("REST API", depth=3) == "api.md"

    def test_default_shallow_is_product(self):
        assert _choose_template("Some Page", depth=0) == "product.md"

    def test_default_deep_is_architecture(self):
        assert _choose_template("Some Deep Page", depth=5) == "architecture.md"


class TestPageManager:
    def _make_manager(self, cfg, summary, renderer, client):
        return PageManager(cfg, renderer, summary, client=client)

    def _base_spec(self):
        return PageSpec(
            title="Test Page",
            template="product.md",
            context={
                "title": "Test Page",
                "status": "Draft",
                "owner": "Test",
                "last_updated": "2026-07-05",
                "scope": "Test",
                "purpose": "Test.",
                "related_pages": [],
                "related_jira_epics": [],
                "dependencies": [],
                "repository_paths": [],
                "open_questions": [],
                "notes": "",
            },
        )

    def test_creates_page_when_not_exists(self, cfg, summary, renderer):
        client = MagicMock(spec=ConfluenceClient)
        client.find_page.return_value = None
        client.create_page.return_value = {
            "id": "999",
            "_links": {"webui": "/pages/999"},
        }

        manager = self._make_manager(cfg, summary, renderer, client)
        page_id = manager.ensure_page(self._base_spec())

        assert page_id == "999"
        client.create_page.assert_called_once()
        assert summary.created[0].title == "Test Page"

    def test_updates_page_when_exists(self, cfg, summary, renderer):
        client = MagicMock(spec=ConfluenceClient)
        client.find_page.return_value = {
            "id": "100",
            "version": {"number": 3},
            "_links": {"webui": "/pages/100"},
        }
        client.update_page.return_value = {
            "id": "100",
            "_links": {"webui": "/pages/100"},
        }

        manager = self._make_manager(cfg, summary, renderer, client)
        page_id = manager.ensure_page(self._base_spec())

        assert page_id == "100"
        client.update_page.assert_called_once()
        assert summary.updated[0].title == "Test Page"

    def test_skips_page_in_resume_mode(self, cfg, summary, renderer):
        cfg.resume = True
        client = MagicMock(spec=ConfluenceClient)
        client.find_page.return_value = {
            "id": "200",
            "version": {"number": 1},
            "_links": {"webui": "/pages/200"},
        }

        manager = self._make_manager(cfg, summary, renderer, client)
        page_id = manager.ensure_page(self._base_spec())

        assert page_id == "200"
        client.update_page.assert_not_called()
        client.create_page.assert_not_called()
        assert summary.skipped[0].title == "Test Page"

    def test_records_failure_on_api_error(self, cfg, summary, renderer):
        client = MagicMock(spec=ConfluenceClient)
        client.find_page.return_value = None
        client.create_page.side_effect = RuntimeError("API error")

        manager = self._make_manager(cfg, summary, renderer, client)
        page_id = manager.ensure_page(self._base_spec())

        assert page_id is None
        assert summary.failed[0].title == "Test Page"

    def test_build_hierarchy_creates_pages_recursively(self, cfg, summary, renderer):
        client = MagicMock(spec=ConfluenceClient)
        client.find_page.return_value = None
        client.create_page.return_value = {
            "id": "300",
            "_links": {"webui": "/pages/300"},
        }

        manager = self._make_manager(cfg, summary, renderer, client)
        tree = {
            "Parent Page": {
                "Child Page A": {},
                "Child Page B": {},
            }
        }
        result = manager.build_hierarchy(tree)

        # All three pages should be created
        assert "Parent Page" in result
        assert "Child Page A" in result
        assert "Child Page B" in result
        assert len(summary.created) == 3
