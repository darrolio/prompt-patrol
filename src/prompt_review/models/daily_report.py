import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_review.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    total_prompts: Mapped[int] = mapped_column(Integer, default=0)
    flagged_count: Mapped[int] = mapped_column(Integer, default=0)
    developer_count: Mapped[int] = mapped_column(Integer, default=0)
    llm_model_used: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    flags = relationship("PromptFlag", back_populates="daily_report")
