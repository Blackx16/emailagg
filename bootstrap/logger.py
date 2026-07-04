"""
logger.py — Structured logging and execution summary for the Engineering OS Bootstrapper.

Provides:
  - Coloured console output via `rich`
  - Rotating file log
  - ExecutionSummary: tracks creations, updates, skips, failures, timing
  - Decorator `@log_step` for automatic step logging
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Module-level console (shared across the bootstrapper)
# ---------------------------------------------------------------------------
console = Console(highlight=True)


# ---------------------------------------------------------------------------
# Log record types
# ---------------------------------------------------------------------------

@dataclass
class PageRecord:
    """Tracks the outcome of a single Confluence/Jira operation."""
    resource_type: str       # "confluence_page" | "jira_issue" | "jira_epic" | ...
    title: str
    status: str              # "created" | "updated" | "skipped" | "failed"
    url: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ExecutionSummary:
    """Accumulates statistics for the entire bootstrap run."""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None

    created: list[PageRecord] = field(default_factory=list)
    updated: list[PageRecord] = field(default_factory=list)
    skipped: list[PageRecord] = field(default_factory=list)
    failed: list[PageRecord] = field(default_factory=list)

    def record(self, rec: PageRecord) -> None:
        match rec.status:
            case "created":
                self.created.append(rec)
            case "updated":
                self.updated.append(rec)
            case "skipped":
                self.skipped.append(rec)
            case "failed":
                self.failed.append(rec)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.updated) + len(self.skipped) + len(self.failed)

    @property
    def elapsed_seconds(self) -> float:
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    def finalise(self) -> None:
        self.end_time = datetime.now(timezone.utc)

    def print_report(self) -> None:
        """Print a rich, coloured summary table to stdout."""
        self.finalise()

        table = Table(title="Engineering OS Bootstrap — Execution Report", show_header=True)
        table.add_column("Outcome", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Details")

        def _fmt_list(records: list[PageRecord], style: str) -> str:
            return "\n".join(
                f"[{style}]{r.resource_type}[/{style}] {r.title}"
                + (f" — {r.error}" if r.error else "")
                for r in records
            ) or "—"

        table.add_row("[green]Created[/green]", str(len(self.created)), _fmt_list(self.created, "green"))
        table.add_row("[yellow]Updated[/yellow]", str(len(self.updated)), _fmt_list(self.updated, "yellow"))
        table.add_row("[blue]Skipped[/blue]", str(len(self.skipped)), _fmt_list(self.skipped, "blue"))
        table.add_row("[red]Failed[/red]", str(len(self.failed)), _fmt_list(self.failed, "red"))
        table.add_row("[bold]Total[/bold]", str(self.total), "")

        console.print(table)
        console.print(
            Panel(
                f"[bold cyan]Elapsed:[/bold cyan] {self.elapsed_seconds:.1f}s\n"
                f"[bold cyan]Finished at:[/bold cyan] {self.end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                title="Summary",
            )
        )

        if self.failed:
            console.print(
                Panel(
                    "\n".join(
                        f"• [red]{r.title}[/red]: {r.error or 'unknown error'}"
                        for r in self.failed
                    ),
                    title="[red]Failures — Action Required[/red]",
                    border_style="red",
                )
            )

    def to_markdown(self) -> str:
        """Return the summary as a Markdown string for persisting to disk."""
        lines: list[str] = [
            "# Engineering OS Bootstrap Report",
            f"**Run started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Run finished:** {(self.end_time or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Elapsed:** {self.elapsed_seconds:.1f}s",
            "",
            "## Summary",
            f"| Outcome | Count |",
            f"|---------|-------|",
            f"| ✅ Created | {len(self.created)} |",
            f"| 🔄 Updated | {len(self.updated)} |",
            f"| ⏭️ Skipped | {len(self.skipped)} |",
            f"| ❌ Failed  | {len(self.failed)} |",
            f"| **Total** | **{self.total}** |",
            "",
        ]

        for section, records in [
            ("Created", self.created),
            ("Updated", self.updated),
            ("Skipped", self.skipped),
            ("Failed", self.failed),
        ]:
            if records:
                lines.append(f"## {section}")
                for r in records:
                    url_part = f" — [{r.url}]({r.url})" if r.url else ""
                    err_part = f" — ⚠️ `{r.error}`" if r.error else ""
                    lines.append(f"- **{r.resource_type}**: {r.title}{url_part}{err_part}")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """
    Configure root logger with a rich console handler and optional file handler.

    Args:
        level:    Log level string (DEBUG|INFO|WARNING|ERROR).
        log_file: If provided, also write logs to this path.

    Returns:
        Configured logger instance.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_path=False,
        )
    ]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )
        handlers.append(fh)

    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True,
    )

    # Silence overly noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("bootstrap")


# ---------------------------------------------------------------------------
# Step decorator
# ---------------------------------------------------------------------------

def log_step(
    logger: logging.Logger,
    summary: ExecutionSummary,
    resource_type: str,
) -> Callable:
    """
    Decorator factory that wraps a function representing a single bootstrap step.

    The wrapped function must return a PageRecord (or None on skip).
    Timing, logging, and summary recording are handled automatically.

    Usage::

        @log_step(log, summary, "confluence_page")
        def create_my_page() -> PageRecord:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[PageRecord]:
            start = time.perf_counter()
            try:
                result: Optional[PageRecord] = fn(*args, **kwargs)
                if result is None:
                    return None
                result.duration_ms = (time.perf_counter() - start) * 1000
                result.resource_type = resource_type

                match result.status:
                    case "created":
                        logger.info("✅ Created  %s: %s", resource_type, result.title)
                    case "updated":
                        logger.info("🔄 Updated  %s: %s", resource_type, result.title)
                    case "skipped":
                        logger.info("⏭️  Skipped  %s: %s", resource_type, result.title)
                    case "failed":
                        logger.error("❌ Failed   %s: %s — %s", resource_type, result.title, result.error)

                summary.record(result)
                return result
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                logger.exception("💥 Unhandled error in %s", fn.__name__)
                rec = PageRecord(
                    resource_type=resource_type,
                    title=str(args[0] if args else fn.__name__),
                    status="failed",
                    error=str(exc),
                    duration_ms=elapsed,
                )
                summary.record(rec)
                return rec

        return wrapper
    return decorator
