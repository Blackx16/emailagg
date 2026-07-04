"""
config.py — Central configuration for the Engineering OS Bootstrapper.

Loads from environment variables or .env file. Supports multiple environments
(dev, staging, prod). All Atlassian credentials, Confluence space IDs, and
Jira project keys are centralised here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BOOTSTRAP_DIR = Path(__file__).parent
TEMPLATES_DIR = BOOTSTRAP_DIR / "templates"
MANIFESTS_DIR = BOOTSTRAP_DIR / "manifests"
OUTPUT_DIR = BOOTSTRAP_DIR / "output"


class AtlassianConfig(BaseSettings):
    """
    All credentials and identifiers needed to talk to Atlassian APIs.

    Values are loaded from environment variables first, then from a .env
    file inside the bootstrap directory if present.
    """

    model_config = SettingsConfigDict(
        env_file=str(BOOTSTRAP_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Atlassian credentials
    atlassian_email: str = Field(
        default="",
        description="Atlassian account email address (set via ATLASSIAN_EMAIL env var)",
    )
    atlassian_api_token: str = Field(
        default="",
        description="Atlassian API token — generate at id.atlassian.com (set via ATLASSIAN_API_TOKEN env var)",
    )
    atlassian_base_url: str = Field(
        default="https://lazyahh.atlassian.net",
        description="Base URL of your Atlassian Cloud instance",
    )

    # Confluence
    confluence_cloud_id: str = Field(
        default="",
        description="Confluence Cloud ID (from Atlassian admin)",
    )
    confluence_root_space_id: str = Field(
        default="",
        description="Space ID for the root Engineering OS space",
    )
    confluence_root_space_key: str = Field(
        default="TWC",
        description="Space key for the Engineering OS space",
    )

    # Jira
    jira_project_key: str = Field(
        default="LAZYA",
        description="Default Jira project key for EmailAgg",
    )
    jira_default_assignee: str = Field(
        default="",
        description="Atlassian account ID of the default assignee",
    )

    # Runtime behaviour
    dry_run: bool = Field(
        default=False,
        description="If True, no write operations are performed",
    )
    resume: bool = Field(
        default=False,
        description="If True, skips pages/issues that already exist",
    )
    max_retries: int = Field(
        default=5,
        description="Maximum number of retry attempts on transient failures",
    )
    retry_backoff_base: float = Field(
        default=2.0,
        description="Exponential backoff base (seconds) for retries",
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR",
    )
    default_labels: list[str] = Field(
        default=["Engineering OS", "Root", "Engineering"],
        description="Labels applied to all created Confluence pages",
    )

    @field_validator("atlassian_base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def upper_log_level(cls, v: str) -> str:
        return v.upper()

    # -----------------------------------------------------------------------
    # Derived helpers
    # -----------------------------------------------------------------------

    @property
    def confluence_rest_url(self) -> str:
        return f"{self.atlassian_base_url}/wiki/rest/api"

    @property
    def confluence_v2_url(self) -> str:
        return f"{self.atlassian_base_url}/wiki/api/v2"

    @property
    def jira_rest_url(self) -> str:
        return f"{self.atlassian_base_url}/rest/api/3"

    @property
    def auth_tuple(self) -> tuple[str, str]:
        """HTTPBasicAuth-compatible (email, token) tuple."""
        return (self.atlassian_email, self.atlassian_api_token)


def load_config(
    dry_run: bool = False,
    resume: bool = False,
    project: Optional[str] = None,
    log_level: str = "INFO",
) -> AtlassianConfig:
    """
    Factory that returns a configured AtlassianConfig instance,
    applying CLI overrides on top of env/file values.

    Args:
        dry_run: Enable dry-run mode (no writes).
        resume:  Skip existing pages/issues.
        project: Optional project key override.
        log_level: Logging verbosity.

    Returns:
        AtlassianConfig instance ready for use.
    """
    cfg = AtlassianConfig(
        dry_run=dry_run,
        resume=resume,
        log_level=log_level,
    )
    if project:
        cfg.jira_project_key = project
    return cfg
