# Prompt Patrol

Engineers prompt AI coding assistants daily, but nobody reviews whether those prompts align with product vision, stories, or roadmap. Code review catches output problems; **Prompt Patrol catches input problems**.

Prompt Patrol collects prompts from AI coding assistants (starting with Claude Code), stores them centrally, and runs a nightly LLM review that flags concerns and summarizes the day's work.

![Prompt Patrol Screenshot](prompt_patrol_screenshot.png)

## How It Works

```
Developer Machine                     Server
+------------------+                  +----------------------------------+
| Claude Code      |    HTTPS POST    |  FastAPI                         |
|   +-- Hook ------+----------------->|    /api/v1/prompts  [ingestion]  |
|   (python script)|                  |    /                [reports]    |
+------------------+                  |    /prompts         [browser]   |
                                      |    /product-docs    [docs mgmt] |
                                      +----------+-------------------------+
                                                 |
                                      +----------v----------+
                                      |    PostgreSQL 16     |
                                      +----------+----------+
                                                 |
                                      +----------v----------+
                                      | Nightly Review (2 AM)|
                                      |  Claude API reviews  |
                                      |  prompts against     |
                                      |  product docs        |
                                      +----------------------+
```

## Quick Start

### 1. Start the Server

**With Docker (recommended):**

```bash
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

docker compose up -d
```

On Windows (PowerShell):

```powershell
copy .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

docker compose up -d
```

**Without Docker:**

```bash
# Requires PostgreSQL 16 running locally
cp .env.example .env
# Edit .env with your DATABASE_URL and ANTHROPIC_API_KEY

pip install -e .
alembic upgrade head
uvicorn prompt_review.main:app --host 0.0.0.0 --port 8000
```

### 2. Register a Developer

```bash
prompt-review register-developer jsmith --display-name "Jane Smith"
# Output:
#   Developer registered: jsmith
#   API Key: a1b2c3d4...
```

### 3. Install the Hook on Developer Machines

#### macOS / Linux

Copy the hook script:

```bash
mkdir -p ~/.prompt-review
cp hook/prompt_review_hook.py ~/.prompt-review/
```

Set environment variables (add to `~/.bashrc`, `~/.zshrc`, or similar):

```bash
export PROMPT_REVIEW_URL="http://your-server:8000"
export PROMPT_REVIEW_API_KEY="a1b2c3d4..."  # from register-developer
```

Or use the install script:

```bash
./hook/install.sh http://your-server:8000 a1b2c3d4...
```

#### Windows

Copy the hook script:

```powershell
mkdir "$env:USERPROFILE\.prompt-review" -Force
copy hook\prompt_review_hook.py "$env:USERPROFILE\.prompt-review\"
```

Set environment variables permanently (PowerShell as your user):

```powershell
[System.Environment]::SetEnvironmentVariable("PROMPT_REVIEW_URL", "http://your-server:8000", "User")
[System.Environment]::SetEnvironmentVariable("PROMPT_REVIEW_API_KEY", "a1b2c3d4...", "User")
```

Or via the GUI: Start menu > search **"Environment Variables"** > **"Edit environment variables for your account"** > **New** for each variable.

> **Note:** After setting permanent env vars on Windows, restart your terminal for them to take effect.

#### Configure Claude Code

Add to `~/.claude/settings.json` (on Windows: `%USERPROFILE%\.claude\settings.json`):

**macOS / Linux:**

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.prompt-review/prompt_review_hook.py"
          }
        ]
      }
    ]
  }
}
```

**Windows:**

On Windows, `python3` does not exist (it's `python`) and `~` path expansion is unreliable in hook commands. Use **full absolute paths with forward slashes** to both Python and the hook script:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "C:/Users/YOUR_USERNAME/anaconda3/python.exe C:/Users/YOUR_USERNAME/.prompt-review/prompt_review_hook.py"
          }
        ]
      }
    ]
  }
}
```

> **Important:** Use **forward slashes** (`C:/Users/...`), not backslashes (`C:\\Users\\...`). Claude Code's hook runner fails silently with escaped backslashes on Windows.

> **Tip:** To find your Python path, run `where python` in Command Prompt or `Get-Command python` in PowerShell. Use the system Python, not a virtualenv Python.

Claude Code picks up hook changes automatically -- no need to restart your session. You can verify with the `/hooks` command.

The hook **always exits 0** -- it never blocks developer workflow. Errors are logged to `~/.prompt-review/hook.log` (on Windows: `%USERPROFILE%\.prompt-review\hook.log`).

### 4. Upload Documents

Upload documents that inform the nightly AI review. There are three categories:

- **Product Docs** -- product vision, roadmap, user stories (flags misalignment)
- **Compliance Docs** -- policies, procedures, regulations (flags compliance concerns)
- **Technical Docs** -- architecture decisions, coding standards (flags technical deviations)

**Via CLI:**

```bash
prompt-review import-docs ./vision/ --doc-type vision
prompt-review import-docs ./policies/ --doc-type compliance
prompt-review import-docs ./architecture/ --doc-type technical
```

**Via Web UI:** Use the sidebar to navigate to Product Docs, Compliance Docs, or Technical Docs, then click "Add Document".

### 5. View Reports

Open `http://your-server:8000` in a browser. Reports are generated automatically at 2 AM daily. To trigger a review manually:

```bash
prompt-review run-review --date 2026-03-17
```

Or click "Run Review Now" on the homepage.

## Web UI Pages

| Page | URL | Description |
|---|---|---|
| Daily Reports | `/` | List of all daily reports with status, prompt counts, flag counts, save counts |
| Report Detail | `/reports/{YYYY-MM-DD}` | AI summary (grouped by project), flagged prompts with severity badges, stats |
| Prompt Browser | `/prompts` | Searchable list with HTMX filtering by date, developer, project, ticket, flag status |
| Product Docs | `/product-docs` | Create, edit, toggle, and delete product documents |
| Compliance Docs | `/compliance-docs` | Manage policies and procedures for compliance review |
| Technical Docs | `/technical-docs` | Manage architecture and coding standards for technical review |

## Document Types

Prompt Patrol uses three categories of documents to inform the nightly AI review. Each has its own section in the sidebar.

**Product Docs** (`/product-docs`) -- Define what the team should be building. Upload product vision, roadmap, user stories, and general product documents. The AI reviews prompts for alignment with these documents.

**Compliance Docs** (`/compliance-docs`) -- Define policies and procedures the team must follow. The AI flags prompts that suggest work which may violate data handling policies, security procedures, or regulatory requirements.

**Technical Docs** (`/technical-docs`) -- Define how the system should be built. Upload architecture decisions, coding standards, and infrastructure patterns. The AI flags prompts that deviate from documented technical standards.

All three doc types support the same CRUD operations: create, edit, toggle active/inactive, and delete. Only active documents are included in the nightly review.

## Flag Types

The nightly review flags prompts across three dimensions: product, compliance, and technical.

**Product flags:**

| Flag | Description |
|---|---|
| `CONFUSION` | Developer going in circles or contradicting earlier prompts |
| `MISALIGNMENT` | Work direction contradicts product vision, roadmap, or stories |
| `INSUFFICIENT_CONTEXT` | Prompt too vague for the AI to produce correct code |
| `BACKTRACKING` | Undoing or reversing earlier work (unclear requirements signal) |

**Compliance flags:**

| Flag | Description |
|---|---|
| `COMPLIANCE` | Prompt suggests work that may violate policies or procedures (data handling, security policy, regulatory) |

**Technical flags:**

| Flag | Description |
|---|---|
| `ARCHITECTURAL` | Deviates from documented system architecture (wrong patterns, service boundaries) |
| `SECURITY` | Potential security concern (auth bypass, injection risk, secrets handling) |
| `PERFORMANCE` | Likely performance issue (N+1 queries, missing indexes, blocking calls) |
| `DEPENDENCY` | Using unauthorized or inappropriate libraries or frameworks |
| `CONVENTION` | Deviates from documented coding standards or conventions |

Each flag has a severity level: **info** (minor observation), **warning** (discuss at standup), or **critical** (immediate PM attention).

The review engine is deliberately judicious -- it does not flag routine debugging, refactoring, test-writing, or exploratory work. Compliance and technical flags are only raised when relevant documents have been uploaded.

## Register a Save

When a PM reviews prompts and discovers one that helped the team catch a problem early (misalignment, confusion, wasted effort), they can **register a save** on that prompt. This creates a record that proves the system's value over time.

**How to register a save:**

1. Open the **Prompt Browser** (`/prompts`)
2. Click on any prompt row to expand it
3. Click the 🛟 **Register a Save** toggle
4. Describe how reviewing this prompt helped the team (e.g. "Caught developer building feature X which was cut from the roadmap last week -- saved ~2 days of wasted effort")
5. Click **Submit Save**

Once saved, the life preserver icon appears on the prompt row. Save counts are displayed on the Daily Reports list and Report Detail pages. To edit a save, click the pencil icon next to it.

## Configuration

All settings are configured via environment variables or a `.env` file in the project root. The `.env` file is the easiest approach on any platform -- just copy `.env.example` and edit the values.

On Windows, you can also set environment variables permanently via PowerShell:

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-xxxxx", "User")
```

Available settings:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://promptreview:promptreview@localhost:5432/promptreview` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key for nightly reviews |
| `REVIEW_MODEL` | `claude-sonnet-4-20250514` | Claude model for reviews |
| `REVIEW_SCHEDULE_HOUR` | `9` | Hour (0-23, **in UTC**) to run nightly review. Convert your local time: e.g. 2 AM PDT = 9, 2 AM EDT = 6, 2 AM CDT = 7 |
| `REVIEW_MAX_DOC_CHARS` | `50000` | Max product doc characters sent to Claude |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/prompts` | Submit a prompt (requires `Authorization: Bearer <key>`) |
| `POST` | `/api/v1/reviews/trigger` | Manually trigger a review (optional `?review_date=YYYY-MM-DD`) |
| `GET` | `/api/v1/health` | Health check with database status |

## CLI Commands

```bash
prompt-review register-developer <username> [--display-name "Name"]
prompt-review import-docs <path> [--doc-type vision|roadmap|story|general]
prompt-review run-review [--date YYYY-MM-DD]
```

## Project Structure

```
prompt-review/
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_prompt_saves.py
├── hook/                       # Client-side hook for dev machines
│   ├── prompt_review_hook.py
│   └── install.sh
├── src/prompt_review/
│   ├── main.py                 # App entry point, scheduler
│   ├── config.py               # Settings from env vars
│   ├── database.py             # SQLAlchemy async engine
│   ├── cli.py                  # CLI commands
│   ├── models/                 # ORM models (6 tables)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/                    # JSON API routes
│   ├── web/                    # HTML page routes
│   ├── services/               # Business logic
│   │   ├── ingestion.py        # Prompt storage + auth
│   │   ├── review_engine.py    # Nightly LLM review
│   │   └── product_docs.py     # Document CRUD
│   ├── templates/              # Jinja2 templates
│   └── static/                 # CSS + HTMX
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (uses SQLite, no PostgreSQL needed)
pytest tests/ -v

# Run server in dev mode
uvicorn prompt_review.main:app --reload
```

## Tech Stack

- **FastAPI** + **Uvicorn** -- async web framework
- **SQLAlchemy 2.0** (async) + **asyncpg** -- ORM + PostgreSQL driver
- **Alembic** -- database migrations
- **Anthropic Claude API** -- nightly prompt review
- **APScheduler** -- in-process cron scheduler
- **Jinja2** + **HTMX** -- server-rendered UI with dynamic filtering
- **PostgreSQL 16** -- data storage
