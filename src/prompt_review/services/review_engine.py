import json
import logging
from datetime import date, datetime, time, timezone
from itertools import groupby
from operator import attrgetter

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prompt_review.config import settings
from prompt_review.models import DailyReport, ProductDoc, Prompt, PromptFlag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a product-alignment reviewer. You analyze prompts that software engineers \
give to AI coding assistants and identify concerns related to product direction, \
compliance, and technical standards.

You will receive:
1. PRODUCT CONTEXT: Documents organized by type:
   - **Product docs** (vision, roadmap, story, general): Define what the team should be building.
   - **Compliance docs**: Policies and procedures the team must follow. Flag violations as "compliance".
   - **Technical docs**: Architecture and coding standards. Flag deviations as technical flags.
2. DAILY PROMPTS: All prompts submitted today, grouped by project, then by developer and session.

Your job is to:
- Write a brief daily summary in markdown, organized by project. Use a ## heading for each project \
prefixed with "Project: " (e.g. "## Project: MyApp"), then summarize what was worked on in that project \
(2-3 paragraphs per project).
- Flag specific prompts that show genuine concerns across product, compliance, and technical dimensions.

Flag types -- Product:
- CONFUSION: Session shows repeated rework, contradicting earlier prompts in the same session.
- MISALIGNMENT: Work direction contradicts product vision, roadmap, or active stories.
- INSUFFICIENT_CONTEXT: Prompt is too vague for the AI to produce correct, product-aligned code.
- BACKTRACKING: Undoing or reversing earlier work, signaling unclear requirements.

Flag types -- Compliance:
- COMPLIANCE: Prompt suggests work that may violate policies or procedures defined in compliance docs \
(e.g. data handling violations, security policy deviations, regulatory risks).

Flag types -- Technical:
- ARCHITECTURAL: Work deviates from documented system architecture (undocumented patterns, service boundaries).
- SECURITY: Potential security concern (auth bypass, injection risk, secrets handling).
- PERFORMANCE: Likely performance issue (N+1 queries, missing indexes, blocking calls in async code).
- DEPENDENCY: Using unauthorized or inappropriate libraries or frameworks.
- CONVENTION: Deviates from documented coding standards or conventions.

Severity levels:
- info: Minor observation, no action needed.
- warning: Worth discussing in next standup.
- critical: Immediate PM attention recommended.

BE JUDICIOUS. Do NOT flag:
- Routine debugging, refactoring, or test-writing.
- Exploratory prompts early in a session.
- Standard development tasks that don't touch product direction, compliance, or technical standards.
- Only flag compliance/technical concerns if relevant docs have been provided.

Respond with valid JSON matching this schema:
{
  "summary": "markdown string",
  "flags": [
    {
      "prompt_index": <int>,
      "flag_type": "confusion|misalignment|insufficient_context|backtracking|compliance|architectural|security|performance|dependency|convention",
      "severity": "info|warning|critical",
      "explanation": "string"
    }
  ]
}

prompt_index refers to the 0-based index in the flat prompt list provided.
If there are no concerns, return an empty flags array. Do not invent problems.

RESPONSIBLE USE:
This tool operates within a corporate context. You MUST NOT exhibit bias based on any \
protected characteristics. Ignore developer names, language proficiency, writing style, \
and any other characteristics that could indicate race, gender, ethnicity, national origin, \
age, or disability when applying judgment.

This analysis is NOT surveillance or performance evaluation. Do not apply any judgment that \
questions the intelligence, competence, or abilities of individual developers. Do not compare \
developers to each other. Do not infer intent behind a developer's actions.

Frame all flags as process, communication, or alignment gaps -- never as individual failings. \
This analysis exists for collaborative issue resolution only.\
"""


def _build_product_context(docs: list[ProductDoc]) -> str:
    priority = {"product": 0, "compliance": 1, "technical": 2}
    sorted_docs = sorted(docs, key=lambda d: (priority.get(d.doc_type, 99), d.created_at))

    parts: list[str] = []
    total_chars = 0
    for doc in sorted_docs:
        if total_chars + len(doc.content) > settings.review_max_doc_chars:
            remaining = settings.review_max_doc_chars - total_chars
            if remaining > 500:
                parts.append(f"### {doc.display_name} ({doc.doc_type})\n{doc.content[:remaining]}...[truncated]")
            break
        parts.append(f"### {doc.display_name} ({doc.doc_type})\n{doc.content}")
        total_chars += len(doc.content)

    return "\n\n".join(parts) if parts else "(No product documents uploaded yet.)"


def _build_prompt_list(prompts: list[Prompt]) -> tuple[str, list[Prompt]]:
    flat_list: list[Prompt] = []
    lines: list[str] = []

    sorted_prompts = sorted(prompts, key=lambda p: (
        p.project_name or "", p.developer.username, p.session_id, p.submitted_at,
    ))

    for project_name, project_prompts in groupby(sorted_prompts, key=lambda p: p.project_name or "Unknown"):
        lines.append(f"\n# Project: {project_name}")
        for dev_name, dev_prompts in groupby(project_prompts, key=lambda p: p.developer.username):
            lines.append(f"\n## Developer: {dev_name}")
            for session_id, session_prompts in groupby(dev_prompts, key=attrgetter("session_id")):
                lines.append(f"\n### Session: {session_id[:12]}...")
                for p in session_prompts:
                    idx = len(flat_list)
                    flat_list.append(p)
                    ticket = f" ({p.ticket_number})" if p.ticket_number else ""
                    timestamp = p.submitted_at.strftime("%H:%M")
                    lines.append(f"\n[{idx}] {timestamp}{ticket}\n{p.prompt_text}")

    return "\n".join(lines), flat_list


async def run_review(session: AsyncSession, target_date: date) -> DailyReport:
    # Check for existing report
    existing = await session.execute(
        select(DailyReport).where(DailyReport.report_date == target_date)
    )
    report = existing.scalar_one_or_none()

    if report and report.status == "completed":
        return report

    if not report:
        report = DailyReport(report_date=target_date, status="running")
        session.add(report)
        await session.flush()
    else:
        report.status = "running"
        report.error_message = None

    report.review_started_at = datetime.now(timezone.utc)
    await session.commit()

    try:
        # Load prompts for the target date
        day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

        prompt_result = await session.execute(
            select(Prompt)
            .options(selectinload(Prompt.developer))
            .where(Prompt.submitted_at >= day_start, Prompt.submitted_at <= day_end)
            .order_by(Prompt.submitted_at)
        )
        prompts = list(prompt_result.scalars().all())

        report.total_prompts = len(prompts)

        if not prompts:
            report.status = "completed"
            report.summary_text = "No prompts were submitted on this date."
            report.flagged_count = 0
            report.developer_count = 0
            report.review_completed_at = datetime.now(timezone.utc)
            await session.commit()
            return report

        # Count unique developers and projects
        developer_ids = {p.developer_id for p in prompts}
        report.developer_count = len(developer_ids)
        project_names = {p.project_name or "Unknown" for p in prompts}

        # Load product docs
        doc_result = await session.execute(
            select(ProductDoc).where(ProductDoc.is_active.is_(True))
        )
        docs = list(doc_result.scalars().all())

        # Build LLM input
        product_context = _build_product_context(docs)
        prompt_text, flat_prompts = _build_prompt_list(prompts)

        user_message = (
            f"# PRODUCT CONTEXT\n\n{product_context}\n\n"
            f"# DAILY PROMPTS ({target_date})\n\n"
            f"Total: {len(flat_prompts)} prompts from {len(developer_ids)} developers across {len(project_names)} projects\n"
            f"{prompt_text}"
        )

        # Call Claude API
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.review_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        report.llm_model_used = settings.review_model

        # Parse response
        response_text = response.content[0].text
        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

        review_data = json.loads(response_text)

        report.summary_text = review_data["summary"]

        # Store flags
        flags = review_data.get("flags", [])
        flagged_count = 0
        for flag_data in flags:
            prompt_idx = flag_data["prompt_index"]
            if 0 <= prompt_idx < len(flat_prompts):
                flag = PromptFlag(
                    prompt_id=flat_prompts[prompt_idx].id,
                    daily_report_id=report.id,
                    flag_type=flag_data["flag_type"],
                    severity=flag_data["severity"],
                    explanation=flag_data["explanation"],
                )
                session.add(flag)
                flagged_count += 1

        report.flagged_count = flagged_count
        report.status = "completed"
        report.review_completed_at = datetime.now(timezone.utc)
        await session.commit()
        return report

    except Exception as e:
        logger.exception("Review failed for %s", target_date)
        report.status = "failed"
        report.error_message = str(e)
        report.review_completed_at = datetime.now(timezone.utc)
        await session.commit()
        return report
