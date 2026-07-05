"""
renderer.py — Jinja2-based Markdown template renderer.

Loads Markdown templates from the `templates/` directory and renders them
with provided context variables. Templates use Jinja2 syntax for variable
substitution, conditionals, and loops.

Usage::

    from bootstrap.renderer import Renderer

    renderer = Renderer()
    html = renderer.render_to_confluence_storage(
        "architecture.md",
        title="Backend",
        owner="Chandraveer",
        status="Active",
        purpose="Handles all API requests.",
    )
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import ChainableUndefined, Environment, FileSystemLoader, TemplateNotFound

from bootstrap.config import TEMPLATES_DIR
from bootstrap.utils import utc_date

logger = logging.getLogger("bootstrap.renderer")


# ---------------------------------------------------------------------------
# Renderer class
# ---------------------------------------------------------------------------

class Renderer:
    """
    Renders Markdown templates to Confluence Storage Format (XHTML-like).

    The rendering pipeline:
        1. Load the Markdown template from `templates/`.
        2. Substitute Jinja2 variables with the provided context.
        3. Convert the resulting Markdown to Confluence Storage Format.

    Args:
        templates_dir: Path to the templates directory (default: TEMPLATES_DIR).
    """

    def __init__(self, templates_dir: Path = TEMPLATES_DIR) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=ChainableUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        # Register global helpers available in all templates
        self._env.globals["utc_date"] = utc_date

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def render_markdown(self, template_name: str, **context: Any) -> str:
        """
        Render a Jinja2 Markdown template with the given context.

        Args:
            template_name: Filename inside the templates directory (e.g., "adr.md").
            **context:     Key-value pairs injected into the template.

        Returns:
            Rendered Markdown string.

        Raises:
            FileNotFoundError: If the template does not exist.
            jinja2.UndefinedError: If a required variable is missing.
        """
        try:
            tmpl = self._env.get_template(template_name)
        except TemplateNotFound:
            raise FileNotFoundError(
                f"Template '{template_name}' not found in {TEMPLATES_DIR}"
            )
        rendered = tmpl.render(**context)
        logger.debug("Rendered template '%s' (%d chars)", template_name, len(rendered))
        return rendered

    def render_to_confluence_storage(self, template_name: str, **context: Any) -> str:
        """
        Render a template and convert the result to Confluence Storage Format.

        Confluence pages use a subset of XHTML (called Storage Format) rather
        than Markdown. This method applies a set of conversion rules to produce
        valid storage-format HTML.

        Args:
            template_name: Template filename.
            **context:     Template variables.

        Returns:
            Confluence Storage Format string (HTML).
        """
        markdown = self.render_markdown(template_name, **context)
        return markdown_to_confluence_storage(markdown)

    def render_inline(self, template_string: str, **context: Any) -> str:
        """
        Render an inline Jinja2 template string (not from a file).

        Useful for dynamically constructed templates or single-line snippets.

        Args:
            template_string: A Jinja2 template string.
            **context:       Variables to substitute.

        Returns:
            Rendered string.
        """
        tmpl = self._env.from_string(template_string)
        return tmpl.render(**context)


# ---------------------------------------------------------------------------
# Markdown → Confluence Storage Format converter
# ---------------------------------------------------------------------------

def markdown_to_confluence_storage(md: str) -> str:
    """
    Convert a Markdown string to Confluence Storage Format (XHTML).

    This is a lightweight, rule-based converter suitable for the structured
    templates used in this bootstrapper. For complex documents, consider
    using a full-featured converter like `confluence-markdown-sync`.

    Conversion rules applied (in order):
      1. Fenced code blocks → ``<ac:structured-macro ac:name="code">``
      2. ATX headings (##–######) → ``<h2>``–``<h6>``
      3. H1 (used only for page titles) → ``<h1>``
      4. Bold and italic inline markup
      5. Inline code → ``<code>``
      6. Horizontal rules
      7. Ordered and unordered lists
      8. Blockquotes
      9. Paragraph wrapping
      10. Jinja2 macro-style Confluence info/warning panels (custom extension)

    Args:
        md: Input Markdown string.

    Returns:
        Confluence Storage Format HTML string.
    """
    lines = md.split("\n")
    output: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    in_list: list[str] = []  # stack of "ul"/"ol"

    def flush_list() -> None:
        while in_list:
            tag = in_list.pop()
            output.append(f"</{tag}>")

    i = 0
    while i < len(lines):
        line = lines[i]

        # ---- Fenced code block ----
        if line.strip().startswith("```"):
            if not in_code_block:
                flush_list()
                in_code_block = True
                code_lang = line.strip()[3:].strip() or "none"
                code_lines = []
            else:
                in_code_block = False
                code_body = "\n".join(code_lines)
                output.append(
                    f'<ac:structured-macro ac:name="code">'
                    f'<ac:parameter ac:name="language">{code_lang}</ac:parameter>'
                    f'<ac:plain-text-body><![CDATA[{code_body}]]></ac:plain-text-body>'
                    f'</ac:structured-macro>'
                )
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # ---- Confluence info/warning macros (custom: > [!INFO] or > [!WARNING]) ----
        panel_match = re.match(r'^> \[!(INFO|WARNING|NOTE|TIP)\]\s*(.*)', line)
        if panel_match:
            flush_list()
            panel_type = panel_match.group(1).lower()
            panel_title = panel_match.group(2).strip()
            # Collect subsequent blockquote lines
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                body_lines.append(lines[i][1:].strip())
                i += 1
            panel_body = " ".join(body_lines)
            output.append(
                f'<ac:structured-macro ac:name="{panel_type}">'
                f'<ac:parameter ac:name="title">{panel_title}</ac:parameter>'
                f'<ac:rich-text-body><p>{panel_body}</p></ac:rich-text-body>'
                f'</ac:structured-macro>'
            )
            continue

        # ---- Headings ----
        heading_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1))
            text = inline_format(heading_match.group(2))
            output.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # ---- Horizontal rule ----
        if re.match(r'^---+$', line.strip()):
            flush_list()
            output.append("<hr/>")
            i += 1
            continue

        # ---- Unordered list ----
        ul_match = re.match(r'^(\s*)[*\-+]\s+(.*)', line)
        if ul_match:
            content = inline_format(ul_match.group(2))
            if not in_list or in_list[-1] != "ul":
                flush_list()
                in_list.append("ul")
                output.append("<ul>")
            output.append(f"<li>{content}</li>")
            i += 1
            continue

        # ---- Ordered list ----
        ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if ol_match:
            content = inline_format(ol_match.group(2))
            if not in_list or in_list[-1] != "ol":
                flush_list()
                in_list.append("ol")
                output.append("<ol>")
            output.append(f"<li>{content}</li>")
            i += 1
            continue

        # ---- Blockquote ----
        bq_match = re.match(r'^>\s?(.*)', line)
        if bq_match:
            flush_list()
            output.append(f"<blockquote><p>{inline_format(bq_match.group(1))}</p></blockquote>")
            i += 1
            continue

        # ---- Empty line ----
        if not line.strip():
            flush_list()
            i += 1
            continue

        # ---- Paragraph ----
        flush_list()
        output.append(f"<p>{inline_format(line)}</p>")
        i += 1

    flush_list()
    return "\n".join(output)


def inline_format(text: str) -> str:
    """Apply inline Markdown formatting to a single line."""
    # Bold + italic
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Strikethrough
    text = re.sub(r'~~(.*?)~~', r'<del>\1</del>', text)
    return text
