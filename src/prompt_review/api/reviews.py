import asyncio
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_review.database import get_session
from prompt_review.services.review_engine import run_review

router = APIRouter(prefix="/api/v1", tags=["reviews"])


@router.post("/reviews/trigger")
async def trigger_review(
    review_date: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    target_date = review_date or date.today()
    try:
        report = await run_review(session, target_date)
        return {
            "status": report.status,
            "report_date": str(report.report_date),
            "total_prompts": report.total_prompts,
            "flagged_count": report.flagged_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
