"""
confluence.py — Idempotent Confluence page manager for the Engineering OS Bootstrapper.

Provides:
  - ConfluenceClient: Low-level authenticated REST client
  - PageManager: High-level idempotent page create/update/find logic
  - Recursive page hierarchy builder driven by manifest data

All write operations respect the `dry_run` flag in config.
All requests go through the shared `with_retry` decorator.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests import Session

from bootstrap.config import AtlassianConfig
from bootstrap.logger import ExecutionSummary, PageRecord
from bootstrap.renderer import Renderer
from bootstrap.utils import (
    RetryableError,
    build_session,
    check_response,
    deep_get,
    utc_date,
    with_retry,
)

logger = logging.getLogger("bootstrap.confluence")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageSpec:
    """
    Specification for a single Confluence page.

    Used as the unit of work passed between the manifest loader,
    the renderer, and the ConfluenceClient.
    """
    title: str
    template: str                      # Template filename (e.g., "architecture.md")
    parent_id: Optional[str] = None    # Confluence page ID of the parent
    space_id: Optional[str] = None     # Overrides the default space from config
    labels: Optional[list[str]] = None # Additional labels for this page
    context: dict[str, Any] = None     # Template rendering variables

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}


# ---------------------------------------------------------------------------
# Low-level Confluence client
# ---------------------------------------------------------------------------

class ConfluenceClient:
    """
    Low-level Confluence REST API v2 client.

    Handles authentication, request execution, and response validation.
    All mutating methods are no-ops when `cfg.dry_run` is True.

    Args:
        cfg:     AtlassianConfig instance.
        session: Optional pre-built requests.Session (for testing).
    """

    def __init__(self, cfg: AtlassianConfig, session: Optional[Session] = None) -> None:
        self._cfg = cfg
        self._session = session or build_session(cfg)
        self._base = cfg.confluence_rest_url
        self._v2 = cfg.confluence_v2_url

    # -----------------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------------

    def find_page(self, space_key: str, title: str) -> Optional[dict[str, Any]]:
        """
        Search for an existing page by space key and exact title.

        Args:
            space_key: The Confluence space key (e.g., "TWC").
            title:     The exact page title to search for.

        Returns:
            The page dict if found, None otherwise.
        """
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "version,ancestors",
        }
        resp = self._get(f"{self._base}/content", params=params)
        results = deep_get(resp, "results") or []
        if results:
            logger.debug("Found existing page: '%s' (id=%s)", title, results[0]["id"])
            return results[0]
        return None

    def find_page_by_id(self, page_id: str) -> Optional[dict[str, Any]]:
        """Fetch a page by its numeric ID."""
        try:
            resp = self._get(f"{self._base}/content/{page_id}")
            return resp
        except Exception:
            return None

    # -----------------------------------------------------------------------
    # Create / Update
    # -----------------------------------------------------------------------

    def create_page(
        self,
        space_id: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new Confluence page.

        Args:
            space_id:  The numeric space ID.
            title:     Page title.
            body:      Confluence Storage Format HTML body.
            parent_id: Optional parent page ID.

        Returns:
            The created page response dict.
        """
        payload: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"id": space_id},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        logger.info("[DRY-RUN] Would create page: '%s'" if self._cfg.dry_run else "Creating page: '%s'", title)
        if self._cfg.dry_run:
            return {"id": "dry-run", "title": title, "_links": {"webui": "#"}}

        return self._post(f"{self._base}/content", payload)

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        current_version: int,
    ) -> dict[str, Any]:
        """
        Update an existing Confluence page to a new version.

        Args:
            page_id:         Numeric page ID.
            title:           Page title (can be unchanged).
            body:            New Confluence Storage Format body.
            current_version: Current version number (incremented by 1 on update).

        Returns:
            The updated page response dict.
        """
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }

        logger.info("[DRY-RUN] Would update page: '%s'" if self._cfg.dry_run else "Updating page: '%s'", title)
        if self._cfg.dry_run:
            return {"id": page_id, "title": title, "_links": {"webui": "#"}}

        return self._put(f"{self._base}/content/{page_id}", payload)

    def add_labels(self, page_id: str, labels: list[str]) -> None:
        """
        Add labels to a Confluence page.

        Args:
            page_id: Numeric page ID.
            labels:  List of label strings to add.
        """
        if not labels or self._cfg.dry_run:
            return
        payload = [{"prefix": "global", "name": label} for label in labels]
        try:
            self._post(f"{self._base}/content/{page_id}/label", payload)
            logger.debug("Added labels %s to page %s", labels, page_id)
        except Exception as exc:
            logger.warning("Could not add labels to page %s: %s", page_id, exc)

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
# High-level page manager
# ---------------------------------------------------------------------------

class PageManager:
    """
    Idempotent Confluence page creator and updater.

    Before every create, searches for an existing page with the same title
    in the same space. If found, updates it. If not found, creates it.
    Tracks all outcomes in the shared ExecutionSummary.

    Args:
        cfg:      AtlassianConfig instance.
        renderer: Renderer instance for converting templates.
        summary:  Shared ExecutionSummary accumulator.
        client:   Optional ConfluenceClient (injected for testing).
    """

    def __init__(
        self,
        cfg: AtlassianConfig,
        renderer: Renderer,
        summary: ExecutionSummary,
        client: Optional[ConfluenceClient] = None,
    ) -> None:
        self._cfg = cfg
        self._renderer = renderer
        self._summary = summary
        self._client = client or ConfluenceClient(cfg)
        self._space_key = cfg.confluence_root_space_key
        self._space_id = cfg.confluence_root_space_id

    def ensure_page(self, spec: PageSpec) -> Optional[str]:
        """
        Idempotently create or update a Confluence page.

        Flow:
            1. Search for existing page by title.
            2. If exists and --resume mode: skip entirely.
            3. If exists: update it.
            4. If not exists: create it.
            5. Add labels.
            6. Return the page ID (or "dry-run" in dry-run mode).

        Args:
            spec: PageSpec describing the page to create/update.

        Returns:
            The Confluence page ID string, or None on failure.
        """
        space_id = spec.space_id or self._space_id
        labels = list(spec.labels or []) + self._cfg.default_labels

        # Build body
        try:
            # Merge title into context (context may already contain 'title')
            ctx = {"title": spec.title, **spec.context}
            body = self._renderer.render_to_confluence_storage(
                spec.template, **ctx
            )
        except Exception as exc:
            logger.error("Template render failed for '%s': %s", spec.title, exc)
            self._summary.record(PageRecord(
                resource_type="confluence_page",
                title=spec.title,
                status="failed",
                error=f"Template error: {exc}",
            ))
            return None

        # Check existence
        existing = self._client.find_page(self._space_key, spec.title)

        if existing:
            page_id = existing["id"]
            web_url = (
                self._cfg.atlassian_base_url
                + "/wiki"
                + deep_get(existing, "_links", "webui", default="")
            )

            if self._cfg.resume:
                self._summary.record(PageRecord(
                    resource_type="confluence_page",
                    title=spec.title,
                    status="skipped",
                    url=web_url,
                ))
                return page_id

            try:
                version = deep_get(existing, "version", "number", default=1)
                self._client.update_page(page_id, spec.title, body, version)
                self._client.add_labels(page_id, labels)
                self._summary.record(PageRecord(
                    resource_type="confluence_page",
                    title=spec.title,
                    status="updated",
                    url=web_url,
                ))
                return page_id
            except Exception as exc:
                logger.error("Failed to update page '%s': %s", spec.title, exc)
                self._summary.record(PageRecord(
                    resource_type="confluence_page",
                    title=spec.title,
                    status="failed",
                    error=str(exc),
                ))
                return None
        else:
            try:
                result = self._client.create_page(space_id, spec.title, body, spec.parent_id)
                page_id = result.get("id", "dry-run")
                web_url = (
                    self._cfg.atlassian_base_url
                    + "/wiki"
                    + deep_get(result, "_links", "webui", default="")
                )
                self._client.add_labels(page_id, labels)
                self._summary.record(PageRecord(
                    resource_type="confluence_page",
                    title=spec.title,
                    status="created",
                    url=web_url,
                ))
                return page_id
            except Exception as exc:
                logger.error("Failed to create page '%s': %s", spec.title, exc)
                self._summary.record(PageRecord(
                    resource_type="confluence_page",
                    title=spec.title,
                    status="failed",
                    error=str(exc),
                ))
                return None

    def build_hierarchy(
        self,
        tree: dict[str, Any],
        parent_id: Optional[str] = None,
        depth: int = 0,
    ) -> dict[str, str]:
        """
        Recursively build a page hierarchy from a manifest tree dict.

        The tree format mirrors the YAML manifest structure:
            {
                "Home": {},
                "Product": {
                    "Product Vision": {},
                    "Roadmap": {},
                }
            }

        For each node, a Confluence page is created or updated via `ensure_page`.
        The page ID is then used as the parent for child nodes.

        Args:
            tree:      Dict mapping page title → child tree.
            parent_id: Confluence page ID of the parent (None = space root).
            depth:     Current recursion depth (for logging indentation).

        Returns:
            Dict mapping page title → page ID for all created pages.
        """
        created: dict[str, str] = {}
        indent = "  " * depth

        for title, children in tree.items():
            logger.info("%s📄 Ensuring page: %s", indent, title)
            template = _choose_template(title, depth)
            spec = PageSpec(
                title=title,
                template=template,
                parent_id=parent_id,
                context=_build_context(title, depth),
            )
            page_id = self.ensure_page(spec)
            if page_id:
                created[title] = page_id
                if isinstance(children, dict) and children:
                    sub = self.build_hierarchy(children, parent_id=page_id, depth=depth + 1)
                    created.update(sub)
                elif isinstance(children, list):
                    # Leaf list form: ["Child A", "Child B"]
                    leaf_tree = {child: {} for child in children}
                    sub = self.build_hierarchy(leaf_tree, parent_id=page_id, depth=depth + 1)
                    created.update(sub)

        return created


# ---------------------------------------------------------------------------
# Template selection heuristics
# ---------------------------------------------------------------------------

_TEMPLATE_MAP: dict[str, str] = {
    "product vision": "product.md",
    "architecture": "architecture.md",
    "backend": "architecture.md",
    "frontend": "architecture.md",
    "database": "architecture.md",
    "queue": "architecture.md",
    "infrastructure": "architecture.md",
    "deployment": "architecture.md",
    "adr": "adr.md",
    "runbook": "runbook.md",
    "api": "api.md",
    "rest": "api.md",
    "webhook": "api.md",
}


def _choose_template(title: str, depth: int) -> str:
    """Pick the most appropriate template for a given page title."""
    lower = title.lower()
    for keyword, template in _TEMPLATE_MAP.items():
        if keyword in lower:
            return template
    # Default: use product.md for top-level, architecture.md deeper
    return "product.md" if depth <= 1 else "architecture.md"


def _build_context(title: str, depth: int) -> dict[str, Any]:
    """Build default template context for a page."""
    return {
        "title": title,
        "status": "Draft",
        "owner": "Chandraveer S Solanki",
        "last_updated": utc_date(),
        "purpose": f"This page documents {title} for the EmailAgg platform.",
        "scope": "EmailAgg v1.0",
        "related_pages": [],
        "related_jira_epics": [],
        "dependencies": [],
        "repository_paths": [],
        "open_questions": [],
        "notes": "",
        "depth": depth,
    }
