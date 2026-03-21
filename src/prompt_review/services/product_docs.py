from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_review.models import ProductDoc
from prompt_review.schemas.product_doc import ProductDocCreate, ProductDocUpdate


async def list_docs(
    session: AsyncSession,
    active_only: bool = False,
    doc_types: list[str] | None = None,
) -> list[ProductDoc]:
    stmt = select(ProductDoc).order_by(ProductDoc.doc_type, ProductDoc.display_name)
    if active_only:
        stmt = stmt.where(ProductDoc.is_active.is_(True))
    if doc_types:
        stmt = stmt.where(ProductDoc.doc_type.in_(doc_types))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_doc(session: AsyncSession, doc_id: UUID) -> ProductDoc | None:
    return await session.get(ProductDoc, doc_id)


async def create_doc(session: AsyncSession, data: ProductDocCreate) -> ProductDoc:
    doc = ProductDoc(
        filename=data.filename,
        display_name=data.display_name,
        content=data.content,
        doc_type=data.doc_type,
        uploaded_by=data.uploaded_by,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def update_doc(session: AsyncSession, doc_id: UUID, data: ProductDocUpdate) -> ProductDoc | None:
    doc = await session.get(ProductDoc, doc_id)
    if not doc:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)
    await session.commit()
    await session.refresh(doc)
    return doc


async def delete_doc(session: AsyncSession, doc_id: UUID) -> bool:
    doc = await session.get(ProductDoc, doc_id)
    if not doc:
        return False
    await session.delete(doc)
    await session.commit()
    return True
