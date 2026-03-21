import markdown
from datetime import date as date_type, datetime, time, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prompt_review.database import get_session
from prompt_review.models import DailyReport, Prompt, PromptFlag, PromptSave

templates = Jinja2Templates(directory="src/prompt_review/templates")
router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(DailyReport).order_by(DailyReport.report_date.desc())
    )
    reports = list(result.scalars().all())

    # Count saves per report date
    save_counts_result = await session.execute(
        select(
            func.date(Prompt.submitted_at).label("dt"),
            func.count(PromptSave.id).label("save_count"),
        )
        .join(PromptSave, PromptSave.prompt_id == Prompt.id)
        .group_by(func.date(Prompt.submitted_at))
    )
    save_count_map = {row.dt: row.save_count for row in save_counts_result.all()}

    return templates.TemplateResponse("index.html", {
        "request": request,
        "reports": reports,
        "save_count_map": save_count_map,
        "active_page": "home",
    })


@router.get("/reports/{report_date}", response_class=HTMLResponse)
async def report_detail(request: Request, report_date: str, session: AsyncSession = Depends(get_session)):
    target = date_type.fromisoformat(report_date)

    result = await session.execute(
        select(DailyReport).where(DailyReport.report_date == target)
    )
    report = result.scalar_one_or_none()
    if not report:
        return HTMLResponse("<h2>Report not found</h2>", status_code=404)

    # Load flags with prompt and developer info
    flags_result = await session.execute(
        select(PromptFlag)
        .where(PromptFlag.daily_report_id == report.id)
        .options(
            selectinload(PromptFlag.prompt).selectinload(Prompt.developer)
        )
        .order_by(
            # Critical first, then warning, then info
            PromptFlag.severity.desc(),
            PromptFlag.created_at,
        )
    )
    flags = list(flags_result.scalars().all())

    # Count saves for this date
    day_start = datetime.combine(target, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target, time.max, tzinfo=timezone.utc)
    save_count_result = await session.execute(
        select(func.count(PromptSave.id))
        .join(Prompt, PromptSave.prompt_id == Prompt.id)
        .where(Prompt.submitted_at >= day_start, Prompt.submitted_at <= day_end)
    )
    save_count = save_count_result.scalar() or 0

    summary_html = markdown.markdown(report.summary_text) if report.summary_text else ""

    return templates.TemplateResponse("report.html", {
        "request": request,
        "report": report,
        "flags": flags,
        "summary_html": summary_html,
        "save_count": save_count,
        "active_page": "home",
    })
