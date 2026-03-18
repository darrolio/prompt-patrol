from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DailyReportResponse(BaseModel):
    id: UUID
    report_date: date
    summary_text: str | None
    total_prompts: int
    flagged_count: int
    developer_count: int
    llm_model_used: str | None
    status: str
    error_message: str | None
    review_started_at: datetime | None
    review_completed_at: datetime | None

    model_config = {"from_attributes": True}


class PromptFlagResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    flag_type: str
    severity: str
    explanation: str

    model_config = {"from_attributes": True}
