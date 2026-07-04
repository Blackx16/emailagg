"""
github.py — Read-only GitHub integration layer for the Engineering OS Bootstrapper.

This module is intentionally read-only. It never modifies the repository.

Provides:
  - GitHubClient: Authenticated GitHub REST API client
  - RepoScanner: Scans repository structure and maps it to Confluence pages
  - CommitReader: Reads and formats commit history
  - ChangelogGenerator: Generates structured changelog entries from commits

Future extensions:
  - Pull request linking
  - Issue-commit cross-referencing
  - Branch protection status reporting
  - GitHub Actions workflow status summary
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger("bootstrap.github")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CommitInfo:
    """Represents a single Git commit."""
    sha: str
    short_sha: str
    author: str
    date: str
    message: str
    subject: str       # First line of the commit message
    body: str          # Remainder of the commit message

    @property
    def commit_type(self) -> str:
        """
        Extract the Conventional Commits type from the subject line.

        e.g., "feat(worker): add queue" → "feat"
             "fix: resolve IMAP error" → "fix"
             "Initial commit"          → "chore"
        """
        match = re.match(r'^(\w+)(?:\([^)]+\))?[!:]', self.subject)
        return match.group(1) if match else "chore"

    @property
    def scope(self) -> Optional[str]:
        """Extract the Conventional Commits scope if present."""
        match = re.match(r'^\w+\(([^)]+)\)', self.subject)
        return match.group(1) if match else None


@dataclass
class FolderNode:
    """Represents a directory in the repository tree."""
    name: str
    path: str
    children: list["FolderNode"] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Local Git reader (subprocess-based, no API calls needed)
# ---------------------------------------------------------------------------

class LocalGitReader:
    """
    Reads Git history and repository structure from a local clone.

    Uses subprocess to call `git` directly, keeping the implementation
    simple and dependency-free. This is intentionally read-only.

    Args:
        repo_path: Absolute path to the repository root.
    """

    def __init__(self, repo_path: Path) -> None:
        self._path = repo_path
        if not (repo_path / ".git").exists():
            raise ValueError(f"Not a Git repository: {repo_path}")

    def _git(self, *args: str) -> str:
        """
        Run a git command and return stdout as a string.

        Args:
            *args: Git command arguments (without the leading "git").

        Returns:
            Decoded stdout string.

        Raises:
            RuntimeError: If the git command fails.
        """
        result = subprocess.run(
            ["git", *args],
            cwd=self._path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def read_commits(self, max_count: int = 100) -> list[CommitInfo]:
        """
        Read the most recent commits from the current branch.

        Args:
            max_count: Maximum number of commits to return.

        Returns:
            List of CommitInfo objects, newest first.
        """
        sep = "|||"
        fmt = f"%H{sep}%h{sep}%an{sep}%ad{sep}%s{sep}%B"
        raw = self._git(
            "log",
            f"-{max_count}",
            f"--pretty=format:{fmt}",
            "--date=short",
        )
        commits: list[CommitInfo] = []
        for line in raw.split("\n"):
            parts = line.split(sep)
            if len(parts) < 5:
                continue
            sha, short_sha, author, date, subject = parts[:5]
            body = parts[5].strip() if len(parts) > 5 else ""
            commits.append(CommitInfo(
                sha=sha,
                short_sha=short_sha,
                author=author,
                date=date,
                message=f"{subject}\n\n{body}".strip(),
                subject=subject,
                body=body,
            ))
        logger.info("Read %d commits from %s", len(commits), self._path)
        return commits

    def scan_structure(
        self,
        ignore: Optional[list[str]] = None,
        max_depth: int = 3,
    ) -> FolderNode:
        """
        Scan the repository directory structure up to `max_depth` levels.

        Args:
            ignore:    Directory/file names to skip (default: common noise).
            max_depth: Maximum recursion depth.

        Returns:
            FolderNode tree rooted at the repository root.
        """
        default_ignore = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            "test_venv", ".DS_Store", "*.pyc", "*.egg-info",
            "dist", "build", ".next", ".cache",
        }
        ignore_set = default_ignore | set(ignore or [])

        def _scan(path: Path, depth: int) -> FolderNode:
            node = FolderNode(name=path.name, path=str(path.relative_to(self._path)))
            if depth == 0:
                return node
            try:
                for child in sorted(path.iterdir()):
                    if child.name in ignore_set or child.name.startswith("."):
                        continue
                    if child.is_dir():
                        node.children.append(_scan(child, depth - 1))
                    else:
                        node.files.append(child.name)
            except PermissionError:
                pass
            return node

        root = _scan(self._path, max_depth)
        root.name = "emailagg"
        return root

    def get_remote_url(self) -> str:
        """Return the remote 'origin' URL."""
        try:
            return self._git("remote", "get-url", "origin")
        except RuntimeError:
            return "unknown"

    def get_current_branch(self) -> str:
        """Return the name of the current branch."""
        try:
            return self._git("rev-parse", "--abbrev-ref", "HEAD")
        except RuntimeError:
            return "unknown"

    def get_tags(self) -> list[str]:
        """Return all Git tags, newest first."""
        try:
            raw = self._git("tag", "--sort=-version:refname")
            return [t for t in raw.split("\n") if t]
        except RuntimeError:
            return []


# ---------------------------------------------------------------------------
# Changelog generator
# ---------------------------------------------------------------------------

class ChangelogGenerator:
    """
    Generates structured changelog entries from commit history.

    Groups commits by type (feat, fix, chore, etc.) and formats them
    as Markdown sections suitable for a Confluence page body.

    Args:
        reader: LocalGitReader instance.
    """

    # Conventional Commits type → human-readable section heading
    TYPE_LABELS: dict[str, str] = {
        "feat": "✨ Features",
        "fix": "🐛 Bug Fixes",
        "chore": "🔧 Chores",
        "docs": "📚 Documentation",
        "refactor": "♻️ Refactoring",
        "test": "🧪 Tests",
        "perf": "⚡ Performance",
        "deploy": "🚀 Deployments",
        "infra": "🏗️ Infrastructure",
        "security": "🔒 Security",
        "ci": "⚙️ CI/CD",
        "style": "💅 Style",
    }

    def __init__(self, reader: LocalGitReader) -> None:
        self._reader = reader

    def generate_markdown(self, max_commits: int = 50) -> str:
        """
        Generate a full Markdown changelog from recent commits.

        Args:
            max_commits: How many commits to include.

        Returns:
            Formatted Markdown string.
        """
        commits = self._reader.read_commits(max_count=max_commits)
        grouped: dict[str, list[CommitInfo]] = {}

        for commit in commits:
            t = commit.commit_type
            grouped.setdefault(t, []).append(commit)

        lines: list[str] = [
            "# EmailAgg Changelog",
            "",
            f"*Auto-generated from Git history — {commits[0].date if commits else 'N/A'}*",
            "",
        ]

        for type_key, label in self.TYPE_LABELS.items():
            entries = grouped.get(type_key, [])
            if not entries:
                continue
            lines.append(f"## {label}")
            lines.append("")
            for commit in entries:
                scope = f"**({commit.scope})** " if commit.scope else ""
                lines.append(
                    f"- {scope}{commit.subject} "
                    f"([`{commit.short_sha}`](https://github.com/Blackx16/emailagg/commit/{commit.sha})) "
                    f"— {commit.author}, {commit.date}"
                )
            lines.append("")

        # Uncategorised commits
        known_types = set(self.TYPE_LABELS.keys())
        other = [c for t, clist in grouped.items() if t not in known_types for c in clist]
        if other:
            lines.append("## Other Changes")
            for commit in other:
                lines.append(
                    f"- {commit.subject} "
                    f"([`{commit.short_sha}`](https://github.com/Blackx16/emailagg/commit/{commit.sha})) "
                    f"— {commit.author}, {commit.date}"
                )
            lines.append("")

        return "\n".join(lines)

    def generate_confluence_storage(self, max_commits: int = 50) -> str:
        """
        Generate a Confluence Storage Format changelog page body.

        Returns:
            Confluence Storage Format HTML string.
        """
        from bootstrap.renderer import markdown_to_confluence_storage
        md = self.generate_markdown(max_commits=max_commits)
        return markdown_to_confluence_storage(md)


# ---------------------------------------------------------------------------
# Repository structure mapper
# ---------------------------------------------------------------------------

class RepoMapper:
    """
    Maps repository directory structure to a Confluence page hierarchy.

    Scans the repository and generates a page tree that mirrors the
    folder structure, allowing Confluence to serve as living documentation
    of the codebase layout.

    Args:
        reader: LocalGitReader instance.
    """

    def __init__(self, reader: LocalGitReader) -> None:
        self._reader = reader

    def to_confluence_page_tree(self) -> dict[str, Any]:
        """
        Scan the repository and return a dict tree compatible with
        PageManager.build_hierarchy().

        Returns:
            Nested dict: { "Folder Name": { "Subfolder": {} } }
        """
        root = self._reader.scan_structure()
        return {_folder_title(root): _node_to_tree(root)}


def _folder_title(node: FolderNode) -> str:
    """Format a folder node name as a Confluence page title."""
    return node.name.replace("-", " ").replace("_", " ").title()


def _node_to_tree(node: FolderNode) -> dict[str, Any]:
    """Recursively convert a FolderNode tree to a dict page tree."""
    return {_folder_title(child): _node_to_tree(child) for child in node.children}
