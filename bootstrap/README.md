# Engineering OS Bootstrapper

> Production-grade, idempotent bootstrapper for initialising an Atlassian workspace as a full **Engineering Operating System**.

Transforms your Confluence and Jira into:

- 📚 **Engineering Memory** — ADRs, runbooks, architecture diagrams
- 🔍 **RAG-ready Knowledge Base** — richly structured pages ready for AI indexing
- 🗺️ **Living Documentation** — auto-generated from Git history and templates
- 🏗️ **Scalable for multiple products** — manifest-driven, config-first architecture
- 🔁 **Idempotent** — safe to run repeatedly, never creates duplicates

---

## Quick Start

### 1. Prerequisites

```bash
Python 3.12+
pip
git (in PATH)
```

### 2. Install dependencies

```bash
cd bootstrap/
pip install -r requirements.txt
```

### 3. Configure credentials

Copy the example config and fill in your values:

```bash
cp .env.example .env
```

Or set environment variables directly:

```bash
export ATLASSIAN_EMAIL="you@example.com"
export ATLASSIAN_API_TOKEN="your-api-token"
export ATLASSIAN_BASE_URL="https://yourorg.atlassian.net"
export CONFLUENCE_ROOT_SPACE_ID="65841"
export JIRA_PROJECT_KEY="LAZYA"
```

### 4. Run the bootstrapper

```bash
# Full bootstrap (Confluence + Jira)
python main.py

# Dry run — simulate without making any changes
python main.py --dry-run

# Resume — skip pages and issues that already exist
python main.py --resume

# Force sync — update all existing pages
python main.py --sync

# Bootstrap only Confluence
python main.py --confluence-only

# Bootstrap only Jira
python main.py --jira-only

# Generate and publish changelog from Git history
python main.py --changelog

# Target a specific project
python main.py --project EmailAgg

# Verbose logging
python main.py --log-level DEBUG
```

---

## Architecture

```
bootstrap/
│
├── main.py           # CLI entry point (click)
├── config.py         # Pydantic settings (env/file)
├── confluence.py     # Idempotent Confluence client + PageManager
├── jira.py           # Idempotent Jira client + JiraBootstrapper
├── github.py         # Read-only Git/GitHub layer
├── templates.py      # Python-native template registry
├── renderer.py       # Jinja2 renderer + Markdown→Confluence converter
├── logger.py         # Structured logging + ExecutionSummary
├── utils.py          # HTTP, retry, slugify, date helpers
│
├── templates/        # Jinja2 Markdown templates
│   ├── product.md    # Mission, vision, roadmap, metrics
│   ├── adr.md        # Architecture Decision Record
│   ├── architecture.md # Components, request flow, failure modes
│   ├── api.md        # REST API docs with examples
│   └── runbook.md    # Ops runbook: steps, validation, rollback
│
├── manifests/        # YAML-driven configuration
│   ├── engineering_os.yaml   # Root Engineering OS hierarchy
│   └── emailagg.yaml         # EmailAgg project definition
│
├── tests/            # Unit tests (pytest)
│   ├── conftest.py
│   ├── test_renderer.py
│   ├── test_utils.py
│   ├── test_jira.py
│   └── test_confluence.py
│
├── output/           # Generated reports and logs
├── requirements.txt
├── .env.example
└── README.md
```

---

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Idempotent** | Every create first searches for existing item; updates if found, creates if not |
| **Retry-safe** | `@with_retry` decorator: exponential backoff, retries on 429/5xx |
| **Dry-run** | `--dry-run` flag: all write operations become no-ops; full simulation |
| **Resume mode** | `--resume` flag: skips items that already exist |
| **Progress reporting** | Rich progress bars + live status via `rich.progress` |
| **Structured logging** | `rich.logging` console + rotating file log in `output/` |
| **Manifest-driven** | Page hierarchy in YAML; Python recursively builds it |
| **Strong typing** | Pydantic models for config; dataclasses for specs |
| **No global state** | All state passed via constructor injection |
| **Modular** | Each module is independently testable with mocked dependencies |

---

## Confluence Page Hierarchy

The bootstrapper creates the following hierarchy:

```
Engineering (root)
├── Projects
│   └── EmailAgg
│       ├── Home
│       ├── Product
│       │   ├── Product Vision
│       │   ├── Roadmap
│       │   ├── Release Notes
│       │   └── Changelog  ← auto-generated from Git
│       ├── Architecture
│       │   ├── Overview
│       │   ├── Backend
│       │   ├── Frontend
│       │   ├── Database
│       │   ├── Queue Architecture
│       │   ├── Infrastructure
│       │   ├── Deployment
│       │   └── External Services
│       ├── ADRs
│       │   ├── ADR-000 Template
│       │   ├── ADR-001 through ADR-020
│       ├── API
│       │   ├── REST API
│       │   ├── Internal APIs
│       │   ├── Authentication
│       │   └── Webhooks
│       ├── Infrastructure
│       │   ├── Docker
│       │   ├── Redis
│       │   ├── Celery
│       │   ├── VPS
│       │   ├── Monitoring
│       │   ├── Logging
│       │   ├── Backups
│       │   └── Nginx
│       ├── Operations
│       │   ├── Runbooks (6 runbooks)
│       │   ├── Incident Response
│       │   ├── Disaster Recovery
│       │   └── Maintenance
│       └── Development
│           ├── Repository Structure
│           ├── Environment Variables
│           ├── Coding Standards
│           └── Technical Debt
├── Templates
├── Engineering Handbook
├── Architecture
├── Runbooks
├── Standards
└── Decision Records
```

Total: **60+ Confluence pages** created on first run.

---

## Jira Bootstrap

| Type | Items |
|------|-------|
| **Epics** | Product, Authentication, Email Sync Engine, Email Forwarding Engine, Mission Control, Telegram Bot, Infrastructure, Monitoring, Security, Deployment, Documentation, Technical Debt |
| **Components** | Backend, Frontend, Worker, Infrastructure, Database, Redis, Docker, Celery, Monitoring, Security, Website, Mission Control, Telegram, Google API, Microsoft Graph |
| **Versions** | Private Beta, Production Beta, v1.0 |
| **Labels** | backend, frontend, infra, security, worker, api, bug, feature, documentation, tech-debt, beta, release |

---

## Templates

All pages are rendered from Jinja2 templates. Every page includes the following standard fields:

| Field | Description |
|-------|-------------|
| `title` | Page title |
| `status` | Draft / Active / Deprecated |
| `owner` | Page owner name |
| `last_updated` | Auto-set to current date |
| `scope` | Product/release scope |
| `purpose` | Why this page exists |
| `related_pages` | Links to related Confluence pages |
| `related_jira_epics` | Linked Jira epics |
| `dependencies` | Technical or service dependencies |
| `repository_paths` | Relevant repo paths |
| `open_questions` | Unresolved questions |
| `notes` | Free-form notes |

### Custom rendering

```python
from bootstrap.renderer import Renderer

renderer = Renderer()

# Render to Markdown
md = renderer.render_markdown(
    "architecture.md",
    title="Backend",
    owner="Chandraveer",
    status="Active",
    purpose="Handles all API requests.",
)

# Render directly to Confluence Storage Format
html = renderer.render_to_confluence_storage(
    "architecture.md",
    title="Backend",
    owner="Chandraveer",
    status="Active",
    purpose="Handles all API requests.",
)
```

---

## Adding a New Product

1. **Create a manifest**: `manifests/newproduct.yaml` (copy `emailagg.yaml` as template)
2. **Register in `engineering_os.yaml`** under `projects:`
3. **Run the bootstrapper**:
   ```bash
   python main.py --project NewProduct
   ```

The bootstrapper will recursively create the full Confluence hierarchy and Jira epics/components/versions as defined in the manifest. No code changes required.

---

## GitHub Integration

The GitHub module (`github.py`) is intentionally **read-only**. It never modifies the repository.

Current capabilities:
- Read Git commit history (local `git` subprocess)
- Categorise commits by Conventional Commits type
- Generate structured changelog (Markdown + Confluence Storage Format)
- Scan repository directory structure → Confluence page tree

Future capabilities (hooks already defined):
- Link commits to Confluence pages
- Link pull requests to ADRs
- Auto-generate API docs from OpenAPI spec
- Map repository folders to architecture pages

---

## Running Tests

```bash
cd /path/to/emailagg/
pip install -r bootstrap/requirements.txt
pip install pytest

pytest bootstrap/tests/ -v
```

All tests use mocked HTTP clients — no live Atlassian API calls during testing.

---

## Output

After each run, the bootstrapper writes to `output/`:

```
output/
├── bootstrap_2026-07-05.log    # Full structured log
└── report_2026-07-05.md        # Markdown summary report
```

The report shows:
- ✅ Created pages/issues
- 🔄 Updated pages/issues
- ⏭️ Skipped (already existed)
- ❌ Failed (with error details)
- Total elapsed time

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ATLASSIAN_EMAIL` | — | Atlassian account email |
| `ATLASSIAN_API_TOKEN` | — | Atlassian API token |
| `ATLASSIAN_BASE_URL` | — | e.g. `https://yourorg.atlassian.net` |
| `CONFLUENCE_CLOUD_ID` | — | Cloud ID from Atlassian admin |
| `CONFLUENCE_ROOT_SPACE_ID` | — | Numeric Confluence space ID |
| `CONFLUENCE_ROOT_SPACE_KEY` | `TWC` | Confluence space key |
| `JIRA_PROJECT_KEY` | `LAZYA` | Jira project key |
| `JIRA_DEFAULT_ASSIGNEE` | — | Atlassian account ID |
| `DRY_RUN` | `false` | Enable dry-run mode |
| `RESUME` | `false` | Skip existing items |
| `MAX_RETRIES` | `5` | Max retry attempts |
| `RETRY_BACKOFF_BASE` | `2.0` | Exponential backoff base (seconds) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Security Note

> **Never commit your `.env` file.** It contains your Atlassian API token.
> The `.env` file is in `.gitignore` by default.
> For CI/CD, use environment secrets (GitHub Actions secrets, etc.).

---

## License

MIT — See repository root for full license.

---

*Built with ❤️ for the EmailAgg Engineering OS. Safe to run multiple times.*
