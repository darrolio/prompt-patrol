from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PromptSubmit(BaseModel):
    session_id: str
    prompt_text: str
    source_tool: str = "claude_code"
    project_name: str | None = None
    ticket_number: str | None = None
    metadata: dict | None = None
    submitted_at: datetime


class PromptResponse(BaseModel):
    id: UUID
    developer_id: UUID
    session_id: str
    prompt_text: str
    source_tool: str
    project_name: str | None
    ticket_number: str | None
    submitted_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
