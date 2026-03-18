from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_review.database import get_session
from prompt_review.schemas.product_doc import ProductDocCreate, ProductDocUpdate
from prompt_review.services import product_docs as doc_service

templates = Jinja2Templates(directory="src/prompt_review/templates")
router = APIRouter(tags=["web"])


@router.get("/product-docs", response_class=HTMLResponse)
async def list_docs(request: Request, session: AsyncSession = Depends(get_session)):
    docs = await doc_service.list_docs(session)
    return templates.TemplateResponse("product_docs.html", {
        "request": request,
        "docs": docs,
        "active_page": "docs",
    })


@router.post("/product-docs")
async def create_doc(
    filename: str = Form(...),
    display_name: str = Form(...),
    content: str = Form(...),
    doc_type: str = Form("general"),
    session: AsyncSession = Depends(get_session),
):
    data = ProductDocCreate(
        filename=filename,
        display_name=display_name,
        content=content,
        doc_type=doc_type,
    )
    await doc_service.create_doc(session, data)
    return RedirectResponse("/product-docs", status_code=303)


@router.get("/product-docs/{doc_id}/edit", response_class=HTMLResponse)
async def edit_doc_form(request: Request, doc_id: UUID, session: AsyncSession = Depends(get_session)):
    doc = await doc_service.get_doc(session, doc_id)
    if not doc:
        return HTMLResponse("<h2>Document not found</h2>", status_code=404)
    return templates.TemplateResponse("product_doc_edit.html", {
        "request": request,
        "doc": doc,
        "active_page": "docs",
    })


@router.post("/product-docs/{doc_id}/edit")
async def update_doc(
    doc_id: UUID,
    display_name: str = Form(...),
    content: str = Form(...),
    doc_type: str = Form("general"),
    session: AsyncSession = Depends(get_session),
):
    data = ProductDocUpdate(display_name=display_name, content=content, doc_type=doc_type)
    await doc_service.update_doc(session, doc_id, data)
    return RedirectResponse("/product-docs", status_code=303)


@router.post("/product-docs/{doc_id}/toggle")
async def toggle_doc(doc_id: UUID, session: AsyncSession = Depends(get_session)):
    doc = await doc_service.get_doc(session, doc_id)
    if doc:
        data = ProductDocUpdate(is_active=not doc.is_active)
        await doc_service.update_doc(session, doc_id, data)
    return RedirectResponse("/product-docs", status_code=303)


@router.post("/product-docs/{doc_id}/delete")
async def delete_doc(doc_id: UUID, session: AsyncSession = Depends(get_session)):
    await doc_service.delete_doc(session, doc_id)
    return RedirectResponse("/product-docs", status_code=303)
