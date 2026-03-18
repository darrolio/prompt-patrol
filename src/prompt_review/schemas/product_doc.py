from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProductDocCreate(BaseModel):
    filename: str
    display_name: str
    content: str
    doc_type: str = "general"
    uploaded_by: str | None = None


class ProductDocUpdate(BaseModel):
    display_name: str | None = None
    content: str | None = None
    doc_type: str | None = None
    is_active: bool | None = None


class ProductDocResponse(BaseModel):
    id: UUID
    filename: str
    display_name: str
    content: str
    doc_type: str
    is_active: bool
    uploaded_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
