import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_review.database import Base


class PromptFlag(Base):
    __tablename__ = "prompt_flags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    prompt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("prompts.id"), nullable=False)
    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("daily_reports.id"), nullable=False
    )
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prompt = relationship("Prompt", back_populates="flags")
    daily_report = relationship("DailyReport", back_populates="flags")
