#!/usr/bin/env python3
"""
Claude Code hook script for Prompt Review.

Captures prompts from Claude Code's UserPromptSubmit hook and sends them
to the Prompt Review server. Always exits 0 to never block the developer.

Install by adding to ~/.claude/settings.json:
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

On Windows, use full absolute paths with FORWARD SLASHES (backslashes fail silently):
  "command": "C:/Users/YOU/anaconda3/python.exe C:/Users/YOU/.prompt-review/prompt_review_hook.py"

Environment variables:
  PROMPT_REVIEW_URL     - Server URL (e.g. http://localhost:8000)
  PROMPT_REVIEW_API_KEY - Developer API key from register-developer command
"""
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Setup logging to file
log_dir = Path.home() / ".prompt-review"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(log_dir / "hook.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("prompt_review_hook")


def get_git_info(cwd: str) -> dict:
    """Extract git branch and remote URL from the working directory."""
    info = {}
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        if branch.returncode == 0:
            info["branch"] = branch.stdout.strip()

        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        if remote.returncode == 0:
            info["remote_url"] = remote.stdout.strip()
    except Exception as e:
        logger.debug("Git info extraction failed: %s", e)
    return info


def extract_ticket_number(branch: str) -> str | None:
    """Try to extract a ticket number like PROJ-1234 from the branch name."""
    match = re.search(r"[A-Z]+-\d+", branch, re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_project_name(cwd: str) -> str:
    """Use the last component of the working directory as project name."""
    return Path(cwd).name


def main():
    try:
        server_url = os.environ.get("PROMPT_REVIEW_URL", "").rstrip("/")
        api_key = os.environ.get("PROMPT_REVIEW_API_KEY", "")

        if not server_url or not api_key:
            logger.debug("PROMPT_REVIEW_URL or PROMPT_REVIEW_API_KEY not set, skipping")
            return

        # Read hook input from stdin
        raw = sys.stdin.read()
        if not raw:
            logger.debug("No input on stdin")
            return

        # Fix Windows backslashes that may not be properly escaped in JSON
        try:
            hook_data = json.loads(raw)
        except json.JSONDecodeError:
            hook_data = json.loads(raw.replace("\\", "\\\\"))
        prompt_text = hook_data.get("prompt", "")
        if not prompt_text:
            return

        session_id = hook_data.get("session_id", "unknown")
        cwd = hook_data.get("cwd", os.getcwd())

        # Enrich with git info
        git_info = get_git_info(cwd)
        branch = git_info.get("branch", "")
        ticket = extract_ticket_number(branch)
        project = extract_project_name(cwd)

        # Build metadata
        metadata = {
            "branch": branch,
            "remote_url": git_info.get("remote_url"),
            "os_user": os.environ.get("USERNAME") or os.environ.get("USER", "unknown"),
            "cwd": cwd,
            "transcript_path": hook_data.get("transcript_path"),
        }

        # Build payload
        payload = {
            "session_id": session_id,
            "prompt_text": prompt_text,
            "source_tool": "claude_code",
            "project_name": project,
            "ticket_number": ticket,
            "metadata": metadata,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        # POST to server (using httpx for async-friendliness, fallback to urllib)
        try:
            import httpx
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{server_url}/api/v1/prompts",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 201:
                    logger.info("Prompt submitted successfully (session=%s)", session_id[:12])
                else:
                    logger.warning("Server returned %d: %s", resp.status_code, resp.text[:200])
        except ImportError:
            # Fallback to urllib if httpx not installed
            import urllib.request
            req = urllib.request.Request(
                f"{server_url}/api/v1/prompts",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                urllib.request.urlopen(req, timeout=10)
                logger.info("Prompt submitted successfully via urllib (session=%s)", session_id[:12])
            except Exception as e:
                logger.warning("urllib POST failed: %s", e)

    except Exception as e:
        logger.error("Hook failed: %s", e, exc_info=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    # Always exit 0 -- never block the developer
    sys.exit(0)
