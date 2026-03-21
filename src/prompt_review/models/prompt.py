import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_review.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    developer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("developers.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_tool: Mapped[str] = mapped_column(String(50), nullable=False, default="claude_code")
    project_name: Mapped[str | None] = mapped_column(String(200))
    ticket_number: Mapped[str | None] = mapped_column(String(50))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    developer = relationship("Developer", back_populates="prompts")
    flags = relationship("PromptFlag", back_populates="prompt")
    save = relationship("PromptSave", back_populates="prompt", uselist=False)
