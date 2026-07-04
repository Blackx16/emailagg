"""
jira.py — Idempotent Jira project bootstrapper for the Engineering OS.

Provides:
  - JiraClient: Low-level authenticated REST v3 client
  - JiraBootstrapper: High-level idempotent issue, epic, component, version creator

Covers:
  - Epic creation (with Epic Name custom field)
  - Component creation
  - Version (release) creation
  - Label application
  - Issue creation and idempotency checks via JQL search
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from requests import Session

from bootstrap.config import AtlassianConfig
from bootstrap.logger import ExecutionSummary, PageRecord
from bootstrap.utils import (
    RetryableError,
    build_session,
    check_response,
    deep_get,
    utc_date,
    with_retry,
)

logger = logging.getLogger("bootstrap.jira")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class EpicSpec:
    """Specification for a Jira Epic."""
    name: str
    description: str = ""
    labels: list[str] = field(default_factory=list)
    priority: str = "Medium"


@dataclass
class ComponentSpec:
    """Specification for a Jira project component."""
    name: str
    description: str = ""
    lead_account_id: Optional[str] = None


@dataclass
class VersionSpec:
    """Specification for a Jira project version (release)."""
    name: str
    description: str = ""
    released: bool = False


# ---------------------------------------------------------------------------
# Low-level Jira REST client
# ---------------------------------------------------------------------------

class JiraClient:
    """
    Low-level Jira REST API v3 client.

    All mutating methods respect the `dry_run` flag. Requests are wrapped
    in the `with_retry` decorator for exponential backoff.

    Args:
        cfg:     AtlassianConfig instance.
        session: Optional pre-built requests.Session (for testing).
    """

    def __init__(self, cfg: AtlassianConfig, session: Optional[Session] = None) -> None:
        self._cfg = cfg
        self._session = session or build_session(cfg)
        self._base = cfg.jira_rest_url
        self._project = cfg.jira_project_key

    # -----------------------------------------------------------------------
    # Issues
    # -----------------------------------------------------------------------

    def search_issues(self, jql: str, fields: str = "summary,status,issuetype") -> list[dict]:
        """
        Run a JQL query and return matching issues.

        Args:
            jql:    JQL query string.
            fields: Comma-separated field names to return.

        Returns:
            List of issue dicts.
        """
        resp = self._get(
            f"{self._base}/search/jql",
            params={"jql": jql, "fields": fields, "maxResults": 50},
        )
        return deep_get(resp, "issues") or []

    def find_issue_by_summary(
        self,
        summary: str,
        issue_type: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Search for an issue by exact summary in the configured project.

        Args:
            summary:    The issue summary to search for.
            issue_type: Optional type filter (e.g., "Epic").

        Returns:
            First matching issue dict, or None.
        """
        jql = f'project = "{self._project}" AND summary ~ "{summary}"'
        if issue_type:
            jql += f' AND issuetype = "{issue_type}"'
        results = self.search_issues(jql)
        # Exact-match filter (JQL ~ is fuzzy)
        for issue in results:
            if issue["fields"]["summary"].strip() == summary.strip():
                return issue
        return None

    def create_issue(
        self,
        summary: str,
        issue_type: str,
        description: str = "",
        labels: Optional[list[str]] = None,
        priority: str = "Medium",
        parent_key: Optional[str] = None,
        custom_fields: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create a new Jira issue.

        Args:
            summary:       Issue summary (title).
            issue_type:    Jira issue type name (e.g., "Epic", "Story", "Task").
            description:   ADF-compatible description text.
            labels:        List of label strings.
            priority:      Priority name.
            parent_key:    Parent issue key for hierarchical types.
            custom_fields: Additional custom field values.

        Returns:
            Created issue response dict.
        """
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
                "description": _adf_doc(description) if description else None,
                "labels": labels or [],
            }
        }

        if parent_key:
            payload["fields"]["parent"] = {"key": parent_key}

        if custom_fields:
            payload["fields"].update(custom_fields)

        # Remove None values
        payload["fields"] = {k: v for k, v in payload["fields"].items() if v is not None}

        logger.info(
            "[DRY-RUN] Would create %s: '%s'" if self._cfg.dry_run else "Creating %s: '%s'",
            issue_type,
            summary,
        )
        if self._cfg.dry_run:
            return {"key": f"{self._project}-DRY", "id": "dry-run"}

        return self._post(f"{self._base}/issue", payload)

    # -----------------------------------------------------------------------
    # Components
    # -----------------------------------------------------------------------

    def list_components(self) -> list[dict]:
        """List all components in the configured project."""
        return self._get(f"{self._base}/project/{self._project}/components")

    def create_component(self, spec: ComponentSpec) -> dict[str, Any]:
        """
        Create a new project component if one with the same name doesn't exist.

        Args:
            spec: ComponentSpec describing the component.

        Returns:
            Created or existing component dict.
        """
        payload: dict[str, Any] = {
            "name": spec.name,
            "description": spec.description,
            "project": self._project,
        }
        if spec.lead_account_id:
            payload["leadAccountId"] = spec.lead_account_id

        if self._cfg.dry_run:
            return {"id": "dry-run", "name": spec.name}

        return self._post(f"{self._base}/component", payload)

    # -----------------------------------------------------------------------
    # Versions
    # -----------------------------------------------------------------------

    def list_versions(self) -> list[dict]:
        """List all versions in the configured project."""
        return self._get(f"{self._base}/project/{self._project}/versions")

    def create_version(self, spec: VersionSpec) -> dict[str, Any]:
        """
        Create a project version (fix version / release).

        Args:
            spec: VersionSpec describing the version.

        Returns:
            Created version dict.
        """
        payload = {
            "name": spec.name,
            "description": spec.description,
            "projectId": self._get_project_id(),
            "released": spec.released,
        }

        if self._cfg.dry_run:
            return {"id": "dry-run", "name": spec.name}

        return self._post(f"{self._base}/version", payload)

    def _get_project_id(self) -> str:
        """Fetch the numeric project ID for the configured project key."""
        data = self._get(f"{self._base}/project/{self._project}")
        return str(data["id"])

    # -----------------------------------------------------------------------
    # Custom fields
    # -----------------------------------------------------------------------

    def get_field_id(self, field_name: str) -> Optional[str]:
        """
        Find the custom field ID for a given field name.

        Args:
            field_name: Display name of the field (e.g., "Epic Name").

        Returns:
            Field ID string (e.g., "customfield_10011"), or None.
        """
        fields = self._get(f"{self._base}/field")
        for f in fields:
            if f.get("name", "").lower() == field_name.lower():
                return f["id"]
        return None

    # -----------------------------------------------------------------------
    # Internal HTTP helpers
    # -----------------------------------------------------------------------

    @with_retry(max_retries=5, backoff_base=2.0)
    def _get(self, url: str, params: Optional[dict] = None) -> Any:
        resp = self._session.get(url, params=params, timeout=self._cfg.request_timeout)
        check_response(resp)
        return resp.json()

    @with_retry(max_retries=5, backoff_base=2.0)
    def _post(self, url: str, payload: Any) -> Any:
        resp = self._session.post(url, json=payload, timeout=self._cfg.request_timeout)
        check_response(resp)
        return resp.json()

    @with_retry(max_retries=5, backoff_base=2.0)
    def _put(self, url: str, payload: Any) -> Any:
        resp = self._session.put(url, json=payload, timeout=self._cfg.request_timeout)
        check_response(resp)
        return resp.json()


# ---------------------------------------------------------------------------
# High-level bootstrapper
# ---------------------------------------------------------------------------

class JiraBootstrapper:
    """
    Idempotent Jira project bootstrapper.

    Orchestrates creation of Epics, Components, Versions, and Labels
    for a Jira project. All operations are idempotency-safe: existing
    items with matching names are skipped.

    Args:
        cfg:     AtlassianConfig instance.
        summary: Shared ExecutionSummary accumulator.
        client:  Optional JiraClient (injected for testing).
    """

    def __init__(
        self,
        cfg: AtlassianConfig,
        summary: ExecutionSummary,
        client: Optional[JiraClient] = None,
    ) -> None:
        self._cfg = cfg
        self._summary = summary
        self._client = client or JiraClient(cfg)

    def bootstrap_epics(self, epic_specs: list[EpicSpec]) -> dict[str, str]:
        """
        Create Epics from a list of EpicSpec objects.

        Skips epics whose summary already exists in the project.
        Returns a mapping of epic name → issue key.
        """
        created: dict[str, str] = {}
        for spec in epic_specs:
            existing = self._client.find_issue_by_summary(spec.name, issue_type="Epic")
            if existing:
                key = existing["key"]
                logger.info("⏭️  Epic already exists: '%s' (%s)", spec.name, key)
                self._summary.record(PageRecord(
                    resource_type="jira_epic",
                    title=spec.name,
                    status="skipped",
                    url=f"{self._cfg.atlassian_base_url}/browse/{key}",
                ))
                created[spec.name] = key
                continue

            try:
                result = self._client.create_issue(
                    summary=spec.name,
                    issue_type="Epic",
                    description=spec.description,
                    labels=spec.labels,
                    priority=spec.priority,
                    custom_fields={"customfield_10011": spec.name},  # Epic Name field
                )
                key = result.get("key", f"{self._cfg.jira_project_key}-DRY")
                self._summary.record(PageRecord(
                    resource_type="jira_epic",
                    title=spec.name,
                    status="created",
                    url=f"{self._cfg.atlassian_base_url}/browse/{key}",
                ))
                created[spec.name] = key
                logger.info("✅ Created Epic: '%s' → %s", spec.name, key)
            except Exception as exc:
                logger.error("❌ Failed to create Epic '%s': %s", spec.name, exc)
                self._summary.record(PageRecord(
                    resource_type="jira_epic",
                    title=spec.name,
                    status="failed",
                    error=str(exc),
                ))

        return created

    def bootstrap_components(self, component_specs: list[ComponentSpec]) -> None:
        """
        Create project components from a list of ComponentSpec objects.

        Skips components with names that already exist.
        """
        existing_names = {c["name"] for c in self._client.list_components()}

        for spec in component_specs:
            if spec.name in existing_names:
                logger.info("⏭️  Component already exists: '%s'", spec.name)
                self._summary.record(PageRecord(
                    resource_type="jira_component",
                    title=spec.name,
                    status="skipped",
                ))
                continue

            try:
                self._client.create_component(spec)
                self._summary.record(PageRecord(
                    resource_type="jira_component",
                    title=spec.name,
                    status="created",
                ))
                logger.info("✅ Created Component: '%s'", spec.name)
            except Exception as exc:
                logger.error("❌ Failed to create Component '%s': %s", spec.name, exc)
                self._summary.record(PageRecord(
                    resource_type="jira_component",
                    title=spec.name,
                    status="failed",
                    error=str(exc),
                ))

    def bootstrap_versions(self, version_specs: list[VersionSpec]) -> None:
        """
        Create project versions from a list of VersionSpec objects.

        Skips versions with names that already exist.
        """
        existing_names = {v["name"] for v in self._client.list_versions()}

        for spec in version_specs:
            if spec.name in existing_names:
                logger.info("⏭️  Version already exists: '%s'", spec.name)
                self._summary.record(PageRecord(
                    resource_type="jira_version",
                    title=spec.name,
                    status="skipped",
                ))
                continue

            try:
                self._client.create_version(spec)
                self._summary.record(PageRecord(
                    resource_type="jira_version",
                    title=spec.name,
                    status="created",
                ))
                logger.info("✅ Created Version: '%s'", spec.name)
            except Exception as exc:
                logger.error("❌ Failed to create Version '%s': %s", spec.name, exc)
                self._summary.record(PageRecord(
                    resource_type="jira_version",
                    title=spec.name,
                    status="failed",
                    error=str(exc),
                ))


# ---------------------------------------------------------------------------
# ADF helpers
# ---------------------------------------------------------------------------

def _adf_doc(text: str) -> dict[str, Any]:
    """
    Wrap plain text in Atlassian Document Format (ADF) structure.

    ADF is the JSON format used for Jira issue description bodies.

    Args:
        text: Plain text to wrap.

    Returns:
        ADF-formatted dict.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    content = [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": para}],
        }
        for para in paragraphs
    ]
    return {
        "version": 1,
        "type": "doc",
        "content": content or [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }
