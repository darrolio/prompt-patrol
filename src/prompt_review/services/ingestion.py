from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_review.models import Developer, Prompt
from prompt_review.schemas.prompt import PromptSubmit
from prompt_review.services.pii_masker import mask_pii


async def authenticate_developer(session: AsyncSession, api_key: str) -> Developer | None:
    result = await session.execute(
        select(Developer).where(Developer.api_key == api_key, Developer.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def store_prompt(session: AsyncSession, developer_id: UUID, data: PromptSubmit) -> Prompt:
    # Server-side PII masking safety net (hook also masks client-side)
    masked_text = mask_pii(data.prompt_text)
    prompt = Prompt(
        developer_id=developer_id,
        session_id=data.session_id,
        prompt_text=masked_text,
        source_tool=data.source_tool,
        project_name=data.project_name,
        ticket_number=data.ticket_number,
        metadata_json=data.metadata,
        submitted_at=data.submitted_at,
    )
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)
    return prompt
