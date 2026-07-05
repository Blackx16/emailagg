# {{ title }}

| Field | Value |
|-------|-------|
| **Status** | {{ status | default("Draft") }} |
| **Owner** | {{ owner | default("Chandraveer S Solanki") }} |
| **Last Updated** | {{ last_updated | default(utc_date()) }} |
| **Scope** | {{ scope | default("EmailAgg v1.0") }} |

---

## Purpose

{{ purpose | default("Documents the architecture of the " ~ title ~ " component, including its responsibilities, dependencies, request flow, and failure modes.") }}

---

## Responsibilities

{{ responsibilities | default("Describe what this component is responsible for. Use a bullet list of core duties.") }}

{% if responsibility_list is defined %}
{% for resp in responsibility_list %}
- {{ resp }}
{% endfor %}
{% else %}
- Handle incoming requests and validate inputs
- Orchestrate downstream service calls
- Return well-structured responses or errors
- Emit metrics and logs for observability
{% endif %}

---

## Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Internal | Primary data store |
| Redis | Internal | Caching, rate limiting, task queue |
| Celery Workers | Internal | Async task execution |
| FastAPI Backend | Internal | REST API gateway |
{% if extra_dependencies is defined %}
{% for dep in extra_dependencies %}
| {{ dep.name }} | {{ dep.type | default("External") }} | {{ dep.purpose }} |
{% endfor %}
{% endif %}

---

## Components

{% if components_list is defined %}
{% for comp in components_list %}
### {{ comp.name }}

{{ comp.description }}

{% endfor %}
{% else %}
### API Layer
Exposes REST endpoints and validates request/response schemas using Pydantic models.

### Service Layer
Contains business logic, orchestrates database queries, and delegates async tasks to Celery.

### Data Layer
SQLAlchemy ORM models, Alembic migrations, and database session management.
{% endif %}

---

## Request Flow

```
{% if request_flow is defined %}
{{ request_flow }}
{% else %}
Client Request
    ↓
Nginx (SSL termination, rate limiting)
    ↓
FastAPI (auth middleware, request validation)
    ↓
Service Layer (business logic)
    ↓
PostgreSQL / Redis (data persistence / caching)
    ↓
Celery Worker (async processing, if needed)
    ↓
Response
{% endif %}
```

---

## Failure Modes

| Failure | Impact | Detection | Recovery |
|---------|--------|-----------|----------|
| Database connection loss | High — all API calls fail | Health check endpoint | Auto-reconnect via SQLAlchemy pool |
| Redis unavailable | Medium — rate limiting disabled | Redis ping check | Fail open with degraded service |
| Celery worker crash | Medium — async tasks queued | Flower monitoring | Celery auto-restart via Docker |
| External API timeout | Low/Medium | Request timeout logs | Exponential backoff, user notification |
{% if failure_modes is defined %}
{% for fm in failure_modes %}
| {{ fm.failure }} | {{ fm.impact }} | {{ fm.detection }} | {{ fm.recovery }} |
{% endfor %}
{% endif %}

---

## Scaling

{{ scaling_notes | default("Horizontal scaling is achieved by running multiple Celery workers and load-balancing FastAPI behind Nginx. The current VPS handles hundreds of active mailboxes. Kubernetes migration is planned post-v1.") }}

---

## Monitoring

- **Health endpoint**: `GET /health` — returns 200 when all dependencies are reachable
- **Celery Flower**: Worker task monitoring at `/flower`
- **Log aggregation**: Application logs written to stdout → Docker log driver
- **Google Drive backup**: Nightly log backup via cron script
- **Metrics**: Request count, latency, error rate, sync lag

{% if monitoring_notes is defined %}
{{ monitoring_notes }}
{% endif %}

---

## Security

- All API endpoints require JWT authentication (internal) or Basic Auth (Mission Control)
- OAuth tokens encrypted at rest using Fernet AES-256
- Internal endpoints (`/internal/`) are blocked at Nginx proxy layer
- Redis and PostgreSQL are on an isolated Docker internal network
- No raw passwords or credentials logged

{% if security_notes is defined %}
{{ security_notes }}
{% endif %}

---

## Future Improvements

{% if future_improvements is defined %}
{% for item in future_improvements %}
- {{ item }}
{% endfor %}
{% else %}
- Migrate to Kubernetes for autoscaling
- Add distributed tracing (OpenTelemetry)
- Implement circuit breaker for external API calls
- Add Prometheus metrics export
- Move secrets to HashiCorp Vault
{% endif %}

---

## Related Pages

{% if related_pages %}
{% for page in related_pages %}
- {{ page }}
{% endfor %}
{% else %}
- Architecture Overview
- Infrastructure
- Deployment
{% endif %}

## Related Jira Epics

{% if related_jira_epics %}
{% for epic in related_jira_epics %}
- {{ epic }}
{% endfor %}
{% else %}
- Infrastructure
- Monitoring & Observability
{% endif %}

## Repository Paths

{% if repository_paths %}
{% for path in repository_paths %}
- `{{ path }}`
{% endfor %}
{% else %}
- `/backend/app/`
{% endif %}

---

## Open Questions

{% if open_questions %}
{% for q in open_questions %}
- [ ] {{ q }}
{% endfor %}
{% else %}
- [ ] What are the autoscaling thresholds for Celery workers?
- [ ] Should we migrate to managed PostgreSQL (e.g., Supabase) for v1?
{% endif %}

## Notes

{{ notes | default("") }}

---

*This page was auto-generated by the Engineering OS Bootstrapper on {{ utc_date() }}.*
