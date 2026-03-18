from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_review.database import get_session
from prompt_review.schemas.prompt import PromptResponse, PromptSubmit
from prompt_review.services.ingestion import authenticate_developer, store_prompt

router = APIRouter(prefix="/api/v1", tags=["prompts"])


@router.post("/prompts", response_model=PromptResponse, status_code=201)
async def submit_prompt(
    data: PromptSubmit,
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
):
    api_key = authorization.removeprefix("Bearer ").strip()
    developer = await authenticate_developer(session, api_key)
    if not developer:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    prompt = await store_prompt(session, developer.id, data)
    return prompt
