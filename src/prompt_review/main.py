import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from prompt_review.config import settings
from prompt_review.database import async_session_factory, engine

logger = logging.getLogger("prompt_review")


async def nightly_review_job():
    """Run the nightly review for yesterday's prompts."""
    from prompt_review.services.review_engine import run_review

    yesterday = date.today()
    # Review yesterday's prompts (job runs at 2 AM)
    from datetime import timedelta
    yesterday = date.today() - timedelta(days=1)

    logger.info("Starting nightly review for %s", yesterday)
    async with async_session_factory() as session:
        try:
            report = await run_review(session, yesterday)
            logger.info(
                "Nightly review completed: date=%s status=%s prompts=%d flags=%d",
                report.report_date, report.status, report.total_prompts, report.flagged_count,
            )
        except Exception:
            logger.exception("Nightly review failed for %s", yesterday)


async def check_missed_reviews():
    """On startup, check for interrupted reviews and re-run them."""
    from sqlalchemy import select
    from prompt_review.models import DailyReport
    from prompt_review.services.review_engine import run_review

    async with async_session_factory() as session:
        result = await session.execute(
            select(DailyReport).where(DailyReport.status == "running")
        )
        interrupted = list(result.scalars().all())
        for report in interrupted:
            logger.warning("Found interrupted review for %s, re-running", report.report_date)
            try:
                await run_review(session, report.report_date)
            except Exception:
                logger.exception("Failed to recover review for %s", report.report_date)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Prompt Review starting up")

    # Startup self-check
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception:
        logger.error("Database connection FAILED - check DATABASE_URL")

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set - nightly reviews will fail")

    # Check for interrupted reviews
    try:
        await check_missed_reviews()
    except Exception:
        logger.warning("Could not check for missed reviews (DB may not be migrated yet)")

    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        nightly_review_job,
        "cron",
        hour=settings.review_schedule_hour,
        minute=0,
        id="nightly_review",
    )
    scheduler.start()
    logger.info("Scheduler started - nightly review at %02d:00", settings.review_schedule_hour)

    yield

    # Shutdown
    scheduler.shutdown()
    await engine.dispose()
    logger.info("Prompt Review shut down")


app = FastAPI(title="Prompt Review", version="0.1.0", lifespan=lifespan)

# Static files
app.mount("/static", StaticFiles(directory="src/prompt_review/static"), name="static")

# API routes
from prompt_review.api.health import router as health_router
from prompt_review.api.prompts import router as prompts_api_router
from prompt_review.api.reviews import router as reviews_router

app.include_router(health_router)
app.include_router(prompts_api_router)
app.include_router(reviews_router)

# Web routes
from prompt_review.web.reports import router as reports_router
from prompt_review.web.prompts import router as prompts_web_router
from prompt_review.web.product_docs import router as product_docs_router

app.include_router(reports_router)
app.include_router(prompts_web_router)
app.include_router(product_docs_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
