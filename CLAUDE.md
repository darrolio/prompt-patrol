# Prompt Patrol - Claude Code Context

## What This Project Is

Prompt Patrol is a product management tool that collects prompts engineers give to AI coding assistants, stores them centrally, and runs nightly LLM reviews to flag misalignment with product vision. Claude Code is the first supported assistant (via `UserPromptSubmit` hook). The web UI uses a VS Code dark theme.

## Tech Stack

- **Python 3.11+**, **FastAPI**, **SQLAlchemy 2.0** (async), **PostgreSQL**, **Jinja2 + HTMX**
- Anthropic Claude API for nightly reviews, APScheduler for scheduling
- Tests use **SQLite** via aiosqlite (no PostgreSQL needed for tests)

## Project Layout

```
src/prompt_review/
  main.py          # FastAPI app, lifespan, APScheduler setup
  config.py        # Pydantic settings from env vars / .env
  database.py      # Async SQLAlchemy engine + session factory
  cli.py           # CLI: register-developer, import-docs, run-review
  models/          # 6 SQLAlchemy ORM models (developer, prompt, daily_report, prompt_flag, prompt_save, product_doc)
  schemas/         # Pydantic request/response schemas
  api/             # JSON API routes (/api/v1/prompts, /api/v1/reviews/trigger, /api/v1/health)
  web/             # HTML page routes (/, /reports/{date}, /prompts, /product-docs)
  services/        # Business logic (ingestion.py, review_engine.py, product_docs.py)
  templates/       # Jinja2 templates (base.html + 5 page templates + partials/ incl. save UI)
  static/          # CSS theme + htmx.min.js
alembic/           # DB migrations (001_initial_schema.py, 002_add_prompt_saves.py)
hook/              # Client-side hook script for developer machines
tests/             # pytest + pytest-asyncio, SQLite test DB
```

## Key Commands

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run server
uvicorn prompt_review.main:app --reload

# Run migrations
alembic upgrade head

# Docker
docker compose up -d --build

# CLI
prompt-review register-developer <username> [--display-name "Name"]
prompt-review import-docs <path> [--doc-type vision|roadmap|story|general]
prompt-review run-review [--date YYYY-MM-DD]
```

## Database

- 6 tables: `developers`, `prompts`, `daily_reports`, `prompt_flags`, `prompt_saves`, `product_docs`
- Models use portable `sqlalchemy.Uuid` (not PostgreSQL-specific UUID) for SQLite test compatibility
- Metadata column uses `sqlalchemy.JSON` (not JSONB) for the same reason
- Migrations are in `alembic/versions/`

## Architecture Decisions

- **Auth**: API-key-per-developer for prompt ingestion; no auth on web UI (internal tool)
- **Hook format**: Uses `matcher` + `hooks` array structure in Claude Code settings.json (not flat object)
- **Hook failure mode**: Always exits 0 -- never blocks the developer
- **Review model**: Sonnet by default (configurable via `REVIEW_MODEL` env var)
- **Scheduler**: APScheduler in-process; on startup checks for interrupted reviews (status="running") and re-runs
- **Frontend**: HTMX + Jinja2, no JS framework -- the `/prompts/list` partial enables filtering without page reload
- **Documents**: Text extracted from uploaded files (PDF, DOCX, TXT, MD) and stored in DB; original files are not kept
- **Doc types**: Three categories -- product, compliance, technical -- each with their own UI section
- **PII masking**: Defense in depth -- hook masks before sending, server masks before storing
- **`source_tool` field**: Designed for extensibility to other AI assistants beyond Claude Code

## Windows-Specific Issues (Resolved)

- **`python3` doesn't exist on Windows** -- hook command must use `python` or full path (e.g. `C:\Users\darry\anaconda3\python.exe`)
- **`~` doesn't expand** in hook commands on Windows -- use full absolute paths in settings.json
- **Windows backslashes in JSON** -- the hook script has a fallback parser that re-escapes backslashes in `cwd` and other paths from Claude Code's stdin input (see `json.loads` try/except block)
- **Forward slashes in hook command** -- Claude Code's hook runner fails silently with escaped backslashes (`C:\\Users\\...`) on Windows; use forward slashes (`C:/Users/...`) in settings.json hook commands
- **Environment variables** -- must restart terminal/Claude Code after adding User Variables for them to take effect. The `.env` file approach is more reliable for the server; env vars are needed for the hook since it runs outside the project directory
- **Hook settings.json path on Windows**: `%USERPROFILE%\.claude\settings.json`
- **Hook log on Windows**: `%USERPROFILE%\.prompt-review\hook.log`
- **User's Python path**: `C:\Users\darry\anaconda3\python.exe`
- **User's current hook command**: `C:/Users/darry/anaconda3/python.exe C:/Users/darry/.prompt-review/prompt_review_hook.py`

## Current Status

- MVP fully implemented and running in Docker (PostgreSQL + FastAPI)
- Hook script installed at `~/.prompt-review/prompt_review_hook.py`
- Hook configured in `~/.claude/settings.json` with forward-slash paths (backslashes fail silently)
- Developer registered (`deaton` / Darryl Eaton), API key set as `PROMPT_REVIEW_API_KEY` env var
- `PROMPT_REVIEW_URL` and `PROMPT_REVIEW_API_KEY` env vars configured and working
- Hook successfully submitting prompts to server with PII masking (verified 2026-03-17)
- Review engine groups prompts by project for per-project summaries
- Prompt browser has project filter dropdown
- "Register a Save" feature fully implemented with inline HTMX UI
- "Run Review Now" button uses HTMX with spinner (no JSON redirect)
- Nightly review scheduled at 9 AM UTC (2 AM PDT)
- Three document sections: Product Docs, Compliance Docs, Technical Docs
- File upload with text extraction (PDF, DOCX, TXT, MD); files not stored
- 10 flag types across product, compliance, and technical dimensions
- Responsible use statement in review engine system prompt
- PII masking on hook (client-side) and server (safety net)

## Future Work

1. **PR-Linked Reviews** -- Attach prompts to a specific pull request so the review and the code change can be evaluated together. This would let PMs see "these prompts led to this PR" and flag alignment issues in the context of the actual deliverable. Implementation TBD -- could use branch name matching, GitHub API integration, or a manual PR link in the prompt browser.

## Workflow Rules

- **Never push to remote without asking first.** Always commit locally and let the user decide when to push.

## Coding Conventions

- Async everywhere: all DB operations use `AsyncSession`
- Models use `Mapped[]` type annotations with `mapped_column()`
- Web routes return `RedirectResponse(status_code=303)` after POST forms
- Services layer separates business logic from routes
- Config via `pydantic-settings` with `.env` file support

## "Register a Save" Feature

- PMs can mark any prompt as a "save" -- documenting how reviewing that prompt helped the team avoid a bad outcome
- 1:1 relationship: one save per prompt (`prompt_saves` table, unique on `prompt_id`)
- UI: life preserver icon (🛟) in prompt browser; expand a prompt to see "Register a Save" toggle
- Inline HTMX forms for create and edit (pencil icon); no page reloads
- Save counts displayed on Daily Reports list and Report Detail stats
- Purpose: builds evidence that the system is effective over time

## Review Engine Details

The nightly review (`services/review_engine.py`):
1. Loads active product docs (priority: vision > roadmap > story > general, capped at 50K chars)
2. Groups prompts by **project**, then by developer + session
3. Calls Claude API with structured system prompt; summary uses per-project `##` headings
4. Expects JSON response: `{ "summary": "markdown", "flags": [...] }`
5. Flag types: `confusion`, `misalignment`, `insufficient_context`, `backtracking`
6. Severity levels: `info`, `warning`, `critical`
7. Failed reviews set `status='failed'` with error message; UI shows retry button

## Web UI Theme

VS Code dark theme colors:
- Background: `#1e1e1e` (primary), `#252526` (sidebar/cards), `#2d2d2d` (tertiary)
- Text: `#d4d4d4` (primary), `#969696` (secondary)
- Accent: `#007acc`, Warning: `#cd9731`, Error: `#f44747`, Success: `#6a9955`
