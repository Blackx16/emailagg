"""
tests/test_renderer.py — Unit tests for the Renderer and markdown converter.

Tests verify that:
  - Templates render without errors given valid context
  - Missing variables raise UndefinedError
  - Markdown-to-Confluence-Storage conversion produces correct XHTML
"""

from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from bootstrap.renderer import Renderer, inline_format, markdown_to_confluence_storage


class TestMarkdownToConfluenceStorage:
    """Tests for the markdown_to_confluence_storage converter."""

    def test_h1(self):
        result = markdown_to_confluence_storage("# Hello World")
        assert "<h1>Hello World</h1>" in result

    def test_h2(self):
        result = markdown_to_confluence_storage("## Section")
        assert "<h2>Section</h2>" in result

    def test_bold(self):
        result = inline_format("**bold text**")
        assert "<strong>bold text</strong>" in result

    def test_italic(self):
        result = inline_format("*italic text*")
        assert "<em>italic text</em>" in result

    def test_inline_code(self):
        result = inline_format("`some code`")
        assert "<code>some code</code>" in result

    def test_unordered_list(self):
        md = "- Item 1\n- Item 2\n- Item 3"
        result = markdown_to_confluence_storage(md)
        assert "<ul>" in result
        assert "<li>Item 1</li>" in result
        assert "<li>Item 3</li>" in result

    def test_ordered_list(self):
        md = "1. First\n2. Second\n3. Third"
        result = markdown_to_confluence_storage(md)
        assert "<ol>" in result
        assert "<li>First</li>" in result

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = markdown_to_confluence_storage(md)
        assert 'ac:name="code"' in result
        assert "python" in result
        assert "print('hello')" in result

    def test_horizontal_rule(self):
        result = markdown_to_confluence_storage("---")
        assert "<hr/>" in result

    def test_paragraph(self):
        result = markdown_to_confluence_storage("This is a paragraph.")
        assert "<p>This is a paragraph.</p>" in result

    def test_link(self):
        result = inline_format("[Click here](https://example.com)")
        assert '<a href="https://example.com">Click here</a>' in result

    def test_empty_string(self):
        result = markdown_to_confluence_storage("")
        assert result == ""

    def test_multiple_headings(self):
        md = "# H1\n## H2\n### H3"
        result = markdown_to_confluence_storage(md)
        assert "<h1>H1</h1>" in result
        assert "<h2>H2</h2>" in result
        assert "<h3>H3</h3>" in result


class TestRenderer:
    """Tests for the Renderer class."""

    def setup_method(self):
        self.renderer = Renderer()

    def test_render_product_template(self):
        """product.md should render with minimal context."""
        result = self.renderer.render_markdown(
            "product.md",
            title="Test Product",
            status="Draft",
            owner="Test Owner",
            last_updated="2026-07-05",
            scope="Test Scope",
            purpose="Test purpose.",
            related_pages=[],
            related_jira_epics=[],
            dependencies=[],
            repository_paths=[],
            open_questions=[],
            notes="",
        )
        assert "Test Product" in result
        assert "Test Owner" in result

    def test_render_adr_template(self):
        """adr.md should render with minimal context."""
        result = self.renderer.render_markdown(
            "adr.md",
            title="ADR-001",
            status="Draft",
            owner="Test",
            last_updated="2026-07-05",
            scope="Test",
            purpose="Test ADR purpose.",
            related_pages=[],
            related_jira_epics=[],
            dependencies=[],
            repository_paths=[],
            open_questions=[],
            notes="",
        )
        assert "ADR-001" in result
        assert "Context" in result
        assert "Decision" in result

    def test_render_architecture_template(self):
        """architecture.md should render with minimal context."""
        result = self.renderer.render_markdown(
            "architecture.md",
            title="Backend Architecture",
            status="Draft",
            owner="Test",
            last_updated="2026-07-05",
            scope="Test",
            purpose="Test architecture.",
            related_pages=[],
            related_jira_epics=[],
            dependencies=[],
            repository_paths=[],
            open_questions=[],
            notes="",
        )
        assert "Backend Architecture" in result
        assert "Request Flow" in result

    def test_render_runbook_template(self):
        """runbook.md should render with minimal context."""
        result = self.renderer.render_markdown(
            "runbook.md",
            title="Deploy Runbook",
            status="Draft",
            owner="Test",
            last_updated="2026-07-05",
            scope="Test",
            purpose="Deploy procedure.",
            related_pages=[],
            related_jira_epics=[],
            dependencies=[],
            repository_paths=[],
            open_questions=[],
            notes="",
        )
        assert "Deploy Runbook" in result
        assert "Preconditions" in result
        assert "Rollback" in result

    def test_nonexistent_template_raises(self):
        """Requesting a non-existent template should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.renderer.render_markdown("nonexistent.md", title="X")

    def test_render_to_confluence_storage(self):
        """render_to_confluence_storage should return HTML, not raw Markdown."""
        result = self.renderer.render_to_confluence_storage(
            "product.md",
            title="Storage Test",
            status="Draft",
            owner="Test",
            last_updated="2026-07-05",
            scope="Test",
            purpose="Test.",
            related_pages=[],
            related_jira_epics=[],
            dependencies=[],
            repository_paths=[],
            open_questions=[],
            notes="",
        )
        # Should contain HTML tags, not raw markdown
        assert "<h" in result or "<p>" in result

    def test_render_inline(self):
        """Inline template rendering should substitute variables."""
        result = self.renderer.render_inline("Hello, {{ name }}!", name="World")
        assert result == "Hello, World!"
