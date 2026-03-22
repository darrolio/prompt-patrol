# Contributing to Prompt Patrol

Thanks for your interest in contributing! Prompt Patrol is an open-source product management tool that reviews AI coding assistant prompts for alignment with product vision, compliance, and technical standards.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for PostgreSQL)
- An Anthropic API key (for running reviews)

### Local Development Setup

```bash
# Clone the repo
git clone https://github.com/darrolio/prompt-patrol.git
cd prompt-patrol

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start PostgreSQL via Docker
docker compose up -d db

# Run migrations
alembic upgrade head

# Start the dev server
uvicorn prompt_review.main:app --reload
```

### Running Tests

Tests use SQLite (no PostgreSQL needed):

```bash
pytest tests/ -v
```

## How to Contribute

### Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version)

### Suggesting Features

Open an issue describing the feature, why it's useful, and how it might work. Discussion before implementation saves everyone time.

### Submitting Changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests if applicable
4. Run `pytest tests/ -v` and make sure all tests pass
5. Open a pull request against `main`

### Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Write a clear description of what changed and why
- Follow the existing code style (async everywhere, services layer for business logic, HTMX for UI interactions)
- Don't introduce new dependencies without discussion

## Code Architecture

- **`src/prompt_review/`** — Main application package
  - `models/` — SQLAlchemy ORM models
  - `services/` — Business logic (review engine, PII masking, doc extraction)
  - `api/` — JSON API endpoints
  - `web/` — HTML page routes
  - `templates/` — Jinja2 templates with HTMX
- **`hook/`** — Client-side hook script for developer machines
- **`tests/`** — pytest test suite
- **`alembic/`** — Database migrations

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.
