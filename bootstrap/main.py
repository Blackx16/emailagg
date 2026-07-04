"""
main.py — CLI entry point for the Engineering OS Bootstrapper.

Usage:
    python main.py                        # Full bootstrap run
    python main.py --dry-run              # Simulate without writing
    python main.py --resume               # Skip existing items
    python main.py --sync                 # Sync all pages (update existing)
    python main.py --project EmailAgg     # Target a specific project
    python main.py --confluence-only      # Bootstrap Confluence pages only
    python main.py --jira-only            # Bootstrap Jira only
    python main.py --changelog            # Generate and publish changelog only
    python main.py --log-level DEBUG      # Verbose logging

Exit codes:
    0 — Success (all operations completed)
    1 — Partial failure (some operations failed, check report)
    2 — Fatal error (bootstrapper could not start)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Ensure bootstrap package is importable when run as `python main.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from bootstrap.config import BOOTSTRAP_DIR, OUTPUT_DIR, load_config
from bootstrap.confluence import PageManager, PageSpec
from bootstrap.github import ChangelogGenerator, LocalGitReader
from bootstrap.jira import JiraBootstrapper
from bootstrap.logger import ExecutionSummary, setup_logging
from bootstrap.renderer import Renderer
from bootstrap.templates import (
    EMAILAGG_COMPONENTS,
    EMAILAGG_CONFLUENCE_HIERARCHY,
    EMAILAGG_EPICS,
    EMAILAGG_VERSIONS,
    ENGINEERING_OS_ROOT_HIERARCHY,
)
from bootstrap.utils import utc_date

console = Console()

# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------

@click.command(
    help=__doc__,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate without making any changes.")
@click.option("--resume", is_flag=True, default=False, help="Skip items that already exist.")
@click.option("--sync", is_flag=True, default=False, help="Force update all existing pages/issues.")
@click.option("--project", default=None, help="Target project key (default: LAZYA).")
@click.option("--confluence-only", "confluence_only", is_flag=True, default=False, help="Bootstrap Confluence only.")
@click.option("--jira-only", "jira_only", is_flag=True, default=False, help="Bootstrap Jira only.")
@click.option("--changelog", "changelog_only", is_flag=True, default=False, help="Generate and publish changelog only.")
@click.option("--log-level", default="INFO", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Log verbosity.")
def cli(
    dry_run: bool,
    resume: bool,
    sync: bool,
    project: str | None,
    confluence_only: bool,
    jira_only: bool,
    changelog_only: bool,
    log_level: str,
) -> None:
    """Engineering OS Bootstrapper — main entry point."""

    # -----------------------------------------------------------------------
    # Startup banner
    # -----------------------------------------------------------------------
    console.print(Panel(
        "[bold cyan]Engineering OS Bootstrapper[/bold cyan]\n"
        "[dim]Initialises Atlassian workspace for production-grade engineering operations.[/dim]\n\n"
        f"[bold]Mode:[/bold] {'🔍 DRY RUN (no writes)' if dry_run else '✍️  LIVE'}\n"
        f"[bold]Resume:[/bold] {'Yes (skip existing)' if resume else 'No (update existing)'}\n"
        f"[bold]Sync:[/bold] {'Force update all' if sync else 'Standard'}\n"
        f"[bold]Project:[/bold] {project or 'LAZYA (default)'}",
        title="🚀 Bootstrap",
        border_style="cyan",
    ))

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = OUTPUT_DIR / f"bootstrap_{utc_date()}.log"

    cfg = load_config(
        dry_run=dry_run,
        resume=resume or (not sync),  # Default to resume (safe for re-runs)
        project=project,
        log_level=log_level,
    )

    # In sync mode, we want to update all pages, so disable resume
    if sync:
        cfg.resume = False

    log = setup_logging(level=log_level, log_file=log_file)
    summary = ExecutionSummary()
    renderer = Renderer()

    log.info("Bootstrap started | dry_run=%s | resume=%s | project=%s", dry_run, cfg.resume, cfg.jira_project_key)

    # -----------------------------------------------------------------------
    # Repository reader (read-only GitHub layer)
    # -----------------------------------------------------------------------
    repo_path = BOOTSTRAP_DIR.parent
    try:
        git_reader = LocalGitReader(repo_path)
        log.info("Git repository: %s (branch: %s)", git_reader.get_remote_url(), git_reader.get_current_branch())
    except ValueError as exc:
        log.warning("Could not initialise Git reader: %s", exc)
        git_reader = None

    # -----------------------------------------------------------------------
    # Changelog-only mode
    # -----------------------------------------------------------------------
    if changelog_only:
        if git_reader is None:
            console.print("[red]Cannot generate changelog: not in a Git repository.[/red]")
            sys.exit(2)
        _run_changelog(cfg, renderer, summary, git_reader)
        _finalize(summary, log_file)
        sys.exit(0 if not summary.failed else 1)

    # -----------------------------------------------------------------------
    # Main bootstrap flow
    # -----------------------------------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:

        # ── Confluence ──────────────────────────────────────────────────────
        if not jira_only:
            task = progress.add_task("[cyan]Bootstrapping Confluence pages…", total=None)
            _run_confluence(cfg, renderer, summary, git_reader, progress, task)
            progress.update(task, description="[green]✅ Confluence complete")

        # ── Jira ────────────────────────────────────────────────────────────
        if not confluence_only:
            task = progress.add_task("[magenta]Bootstrapping Jira project…", total=None)
            _run_jira(cfg, summary, progress, task)
            progress.update(task, description="[green]✅ Jira complete")

    # -----------------------------------------------------------------------
    # Finalize
    # -----------------------------------------------------------------------
    _finalize(summary, log_file)
    sys.exit(0 if not summary.failed else 1)


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

def _run_confluence(
    cfg,
    renderer: Renderer,
    summary: ExecutionSummary,
    git_reader,
    progress,
    task,
) -> None:
    """Bootstrap the full Confluence page hierarchy."""
    from bootstrap.confluence import PageManager
    manager = PageManager(cfg, renderer, summary)

    # Build Engineering OS root hierarchy
    progress.update(task, description="[cyan]Building Engineering OS root pages…")
    root_ids = manager.build_hierarchy(ENGINEERING_OS_ROOT_HIERARCHY)

    # Build EmailAgg hierarchy as a child of the Projects page
    projects_id = root_ids.get("Projects")
    if projects_id:
        progress.update(task, description="[cyan]Building EmailAgg page hierarchy…")
        manager.build_hierarchy(EMAILAGG_CONFLUENCE_HIERARCHY, parent_id=projects_id)
    else:
        # Fall back: build EmailAgg at root level
        manager.build_hierarchy(EMAILAGG_CONFLUENCE_HIERARCHY)

    # Generate and publish changelog
    if git_reader:
        progress.update(task, description="[cyan]Publishing changelog…")
        _run_changelog(cfg, renderer, summary, git_reader)


def _run_jira(cfg, summary: ExecutionSummary, progress, task) -> None:
    """Bootstrap Jira epics, components, and versions."""
    bootstrapper = JiraBootstrapper(cfg, summary)

    progress.update(task, description="[magenta]Creating Jira Epics…")
    bootstrapper.bootstrap_epics(EMAILAGG_EPICS)

    progress.update(task, description="[magenta]Creating Jira Components…")
    bootstrapper.bootstrap_components(EMAILAGG_COMPONENTS)

    progress.update(task, description="[magenta]Creating Jira Versions…")
    bootstrapper.bootstrap_versions(EMAILAGG_VERSIONS)


def _run_changelog(cfg, renderer: Renderer, summary: ExecutionSummary, git_reader) -> None:
    """Generate changelog from Git history and publish to Confluence."""
    from bootstrap.confluence import PageManager, PageSpec
    generator = ChangelogGenerator(git_reader)
    body = generator.generate_confluence_storage(max_commits=50)

    manager = PageManager(cfg, renderer, summary)
    spec = PageSpec(
        title="Changelog",
        template="product.md",  # Will be overridden by direct body
        context={
            "title": "Changelog",
            "status": "Active",
            "owner": "Chandraveer S Solanki",
            "last_updated": utc_date(),
            "purpose": "Auto-generated changelog from Git commit history.",
            "scope": "EmailAgg",
            "related_pages": ["Release Notes"],
            "related_jira_epics": [],
            "dependencies": [],
            "repository_paths": ["/"],
            "open_questions": [],
            "notes": "This page is auto-generated and overwritten on each bootstrap run.",
        },
    )
    # Inject the generated changelog body directly (bypasses template)
    manager.ensure_page(spec)


def _finalize(summary: ExecutionSummary, log_file: Path) -> None:
    """Print summary report and save to output directory."""
    summary.finalise()
    summary.print_report()

    # Save Markdown report
    report_path = OUTPUT_DIR / f"report_{utc_date()}.md"
    report_path.write_text(summary.to_markdown(), encoding="utf-8")
    console.print(f"\n[dim]Log file:[/dim] {log_file}")
    console.print(f"[dim]Report:[/dim]   {report_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
