"""
tests/test_jira.py — Unit tests for JiraClient and JiraBootstrapper.

Uses unittest.mock to stub HTTP responses, ensuring no live API calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bootstrap.config import AtlassianConfig
from bootstrap.jira import JiraBootstrapper, JiraClient, _adf_doc
from bootstrap.jira import ComponentSpec, EpicSpec, VersionSpec
from bootstrap.logger import ExecutionSummary


@pytest.fixture
def cfg():
    return AtlassianConfig(
        atlassian_email="test@example.com",
        atlassian_api_token="test-token",
        atlassian_base_url="https://test.atlassian.net",
        confluence_cloud_id="test-cloud-id",
        confluence_root_space_id="12345",
        confluence_root_space_key="TEST",
        jira_project_key="TEST",
        jira_default_assignee="test-user-id",
        dry_run=True,
        resume=False,
    )


@pytest.fixture
def summary():
    return ExecutionSummary()


class TestJiraClientDryRun:
    """Tests that dry_run=True never calls the live API."""

    def test_create_issue_dry_run(self, cfg):
        client = JiraClient(cfg)
        result = client.create_issue(
            summary="Test Epic",
            issue_type="Epic",
            description="Test description",
        )
        assert result["key"] == "TEST-DRY"

    def test_create_component_dry_run(self, cfg):
        client = JiraClient(cfg)
        result = client.create_component(ComponentSpec(name="Backend"))
        assert result["id"] == "dry-run"

    def test_create_version_dry_run(self, cfg):
        client = JiraClient(cfg)
        # _get_project_id will fail in dry_run, so we patch it
        client._get_project_id = lambda: "12345"
        result = client.create_version(VersionSpec(name="v1.0"))
        assert result["id"] == "dry-run"


class TestJiraBootstrapper:
    """Tests for JiraBootstrapper idempotency logic."""

    def test_skips_existing_epic(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.find_issue_by_summary.return_value = {
            "key": "TEST-1",
            "fields": {"summary": "Authentication"},
        }

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        result = bootstrapper.bootstrap_epics([
            EpicSpec(name="Authentication", description="Auth epic")
        ])

        assert result["Authentication"] == "TEST-1"
        client.create_issue.assert_not_called()
        assert summary.skipped[0].title == "Authentication"

    def test_creates_new_epic(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.find_issue_by_summary.return_value = None
        client.create_issue.return_value = {"key": "TEST-42"}

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        result = bootstrapper.bootstrap_epics([
            EpicSpec(name="New Feature", description="A new epic")
        ])

        assert result["New Feature"] == "TEST-42"
        client.create_issue.assert_called_once()
        assert summary.created[0].title == "New Feature"

    def test_skips_existing_component(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.list_components.return_value = [{"name": "Backend"}]

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        bootstrapper.bootstrap_components([ComponentSpec(name="Backend")])

        client.create_component.assert_not_called()
        assert summary.skipped[0].title == "Backend"

    def test_creates_new_component(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.list_components.return_value = []
        client.create_component.return_value = {"id": "10", "name": "Worker"}

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        bootstrapper.bootstrap_components([ComponentSpec(name="Worker")])

        client.create_component.assert_called_once()
        assert summary.created[0].title == "Worker"

    def test_skips_existing_version(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.list_versions.return_value = [{"name": "v1.0"}]

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        bootstrapper.bootstrap_versions([VersionSpec(name="v1.0")])

        client.create_version.assert_not_called()
        assert summary.skipped[0].title == "v1.0"

    def test_handles_failed_epic_gracefully(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.find_issue_by_summary.return_value = None
        client.create_issue.side_effect = RuntimeError("API error")

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        result = bootstrapper.bootstrap_epics([
            EpicSpec(name="Broken Epic", description="Will fail")
        ])

        assert "Broken Epic" not in result
        assert summary.failed[0].title == "Broken Epic"

    def test_handles_epic_name_field_missing_fallback(self, cfg, summary):
        client = MagicMock(spec=JiraClient)
        client.find_issue_by_summary.return_value = None
        client.create_issue.side_effect = [
            RuntimeError("customfield_10011 is not on the appropriate screen"),
            {"key": "TEST-42"}
        ]

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        result = bootstrapper.bootstrap_epics([
            EpicSpec(name="Fallback Epic", description="Fallback test")
        ])

        assert result["Fallback Epic"] == "TEST-42"
        assert client.create_issue.call_count == 2
        assert summary.created[0].title == "Fallback Epic"

    def test_ensure_project_skips_when_exists(self, cfg, summary):
        cfg.dry_run = False
        client = MagicMock(spec=JiraClient)
        # Mock _base and _project attributes on the mock client
        client._base = "https://test.atlassian.net"
        client._project = "TEST"
        client._get.return_value = {"id": "12345", "key": "TEST"}

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        bootstrapper.ensure_project()

        client._get.assert_called_once_with("https://test.atlassian.net/project/TEST")
        client._post.assert_not_called()
        assert summary.skipped[0].title == "TEST"

    def test_ensure_project_creates_when_missing(self, cfg, summary):
        cfg.dry_run = False
        client = MagicMock(spec=JiraClient)
        client._base = "https://test.atlassian.net"
        client._project = "TEST"
        client._get.side_effect = RuntimeError("Not found")
        client._post.return_value = {"id": "12345", "key": "TEST"}

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        bootstrapper.ensure_project()

        client._get.assert_called_once_with("https://test.atlassian.net/project/TEST")
        client._post.assert_called_once()
        assert summary.created[0].title == "TEST"

    def test_ensure_project_fails(self, cfg, summary):
        cfg.dry_run = False
        client = MagicMock(spec=JiraClient)
        client._base = "https://test.atlassian.net"
        client._project = "TEST"
        client._get.side_effect = RuntimeError("Not found")
        client._post.side_effect = RuntimeError("Create failed")

        bootstrapper = JiraBootstrapper(cfg, summary, client=client)
        with pytest.raises(RuntimeError):
            bootstrapper.ensure_project()

        assert summary.failed[0].title == "TEST"



class TestAdfDoc:
    """Tests for the ADF formatter."""

    def test_single_paragraph(self):
        result = _adf_doc("Hello world")
        assert result["type"] == "doc"
        assert result["version"] == 1
        assert result["content"][0]["type"] == "paragraph"

    def test_multiple_paragraphs(self):
        result = _adf_doc("Paragraph one.\n\nParagraph two.")
        assert len(result["content"]) == 2

    def test_empty_string(self):
        result = _adf_doc("")
        assert result["type"] == "doc"
