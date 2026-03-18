from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prompt_review.database import get_session
from prompt_review.models import Developer, Prompt

templates = Jinja2Templates(directory="src/prompt_review/templates")
router = APIRouter(tags=["web"])


async def _query_prompts(
    session: AsyncSession,
    start_date: str | None,
    end_date: str | None,
    developer_id: str | None,
    ticket: str | None,
    flag_status: str | None,
) -> list[Prompt]:
    stmt = (
        select(Prompt)
        .options(
            selectinload(Prompt.developer),
            selectinload(Prompt.flags),
        )
        .order_by(Prompt.submitted_at.desc())
    )

    if start_date:
        d = date.fromisoformat(start_date)
        stmt = stmt.where(Prompt.submitted_at >= datetime.combine(d, time.min, tzinfo=timezone.utc))
    if end_date:
        d = date.fromisoformat(end_date)
        stmt = stmt.where(Prompt.submitted_at <= datetime.combine(d, time.max, tzinfo=timezone.utc))
    if developer_id:
        stmt = stmt.where(Prompt.developer_id == UUID(developer_id))
    if ticket:
        stmt = stmt.where(Prompt.ticket_number.ilike(f"%{ticket}%"))

    result = await session.execute(stmt)
    prompts = list(result.scalars().all())

    if flag_status == "flagged":
        prompts = [p for p in prompts if p.flags]
    elif flag_status == "clean":
        prompts = [p for p in prompts if not p.flags]

    return prompts


@router.get("/prompts", response_class=HTMLResponse)
async def prompt_browser(
    request: Request,
    date: str | None = Query(None),
    start_date: str | None = None,
    end_date: str | None = None,
    developer: str | None = None,
    ticket: str | None = None,
    flag_status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    today = str(datetime.now(timezone.utc).date())
    # Support both ?date= (from report link) and ?start_date=&end_date= (from filters)
    start_date = start_date or date or today
    end_date = end_date or date or today

    devs_result = await session.execute(
        select(Developer).where(Developer.is_active.is_(True)).order_by(Developer.display_name)
    )
    developers = list(devs_result.scalars().all())

    prompts = await _query_prompts(session, start_date, end_date, developer, ticket, flag_status)

    return templates.TemplateResponse("prompts.html", {
        "request": request,
        "prompts": prompts,
        "developers": developers,
        "start_date": start_date,
        "end_date": end_date,
        "selected_developer": developer or "",
        "ticket": ticket or "",
        "flag_status": flag_status or "",
        "active_page": "prompts",
    })


@router.get("/prompts/list", response_class=HTMLResponse)
async def prompt_list_partial(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    developer: str | None = None,
    ticket: str | None = None,
    flag_status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    prompts = await _query_prompts(session, start_date, end_date, developer, ticket, flag_status)
    return templates.TemplateResponse("partials/prompt_list.html", {
        "request": request,
        "prompts": prompts,
    })
