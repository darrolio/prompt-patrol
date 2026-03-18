import markdown
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prompt_review.database import get_session
from prompt_review.models import DailyReport, PromptFlag

templates = Jinja2Templates(directory="src/prompt_review/templates")
router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(DailyReport).order_by(DailyReport.report_date.desc())
    )
    reports = list(result.scalars().all())
    return templates.TemplateResponse("index.html", {
        "request": request,
        "reports": reports,
        "active_page": "home",
    })


@router.get("/reports/{report_date}", response_class=HTMLResponse)
async def report_detail(request: Request, report_date: str, session: AsyncSession = Depends(get_session)):
    from datetime import date as date_type
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
            selectinload(PromptFlag.prompt).selectinload("developer")
        )
        .order_by(
            # Critical first, then warning, then info
            PromptFlag.severity.desc(),
            PromptFlag.created_at,
        )
    )
    flags = list(flags_result.scalars().all())

    summary_html = markdown.markdown(report.summary_text) if report.summary_text else ""

    return templates.TemplateResponse("report.html", {
        "request": request,
        "report": report,
        "flags": flags,
        "summary_html": summary_html,
        "active_page": "home",
    })
