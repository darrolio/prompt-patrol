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

# Configuration for each doc section
DOC_SECTIONS = {
    "product-docs": {
        "active_page": "docs",
        "page_title": "Product Documents",
        "page_description": "Manage the product documents that inform nightly prompt reviews",
        "doc_types": ["vision", "roadmap", "story", "general"],
        "type_options": [("vision", "Vision"), ("roadmap", "Roadmap"), ("story", "Story"), ("general", "General")],
        "default_type": "general",
        "filename_placeholder": "product-vision-2026.md",
        "name_placeholder": "Product Vision 2026",
        "empty_message": "No product documents uploaded yet. Add vision, roadmap, or story documents to inform nightly reviews.",
    },
    "compliance-docs": {
        "active_page": "compliance",
        "page_title": "Compliance Documents",
        "page_description": "Policies and procedures used to flag compliance concerns in prompts",
        "doc_types": ["compliance"],
        "type_options": [("compliance", "Compliance")],
        "default_type": "compliance",
        "filename_placeholder": "data-handling-policy.md",
        "name_placeholder": "Data Handling Policy",
        "empty_message": "No compliance documents uploaded yet. Add policies and procedures to flag compliance concerns during reviews.",
    },
    "technical-docs": {
        "active_page": "technical",
        "page_title": "Technical Documents",
        "page_description": "Architecture and standards used to flag technical concerns in prompts",
        "doc_types": ["technical"],
        "type_options": [("technical", "Technical")],
        "default_type": "technical",
        "filename_placeholder": "system-architecture.md",
        "name_placeholder": "System Architecture Guide",
        "empty_message": "No technical documents uploaded yet. Add architecture and standards docs to flag technical concerns during reviews.",
    },
}


def _get_section(section: str) -> dict:
    return DOC_SECTIONS[section]


def _redirect_for_doc(doc, default_section: str) -> str:
    """Determine which section URL a doc belongs to based on its doc_type."""
    for section_key, config in DOC_SECTIONS.items():
        if doc.doc_type in config["doc_types"]:
            return f"/{section_key}"
    return f"/{default_section}"


# Generate routes for each doc section
for section_key, config in DOC_SECTIONS.items():
    base_url = f"/{section_key}"

    # List page
    @router.get(base_url, response_class=HTMLResponse, name=f"list_{section_key.replace('-', '_')}")
    async def list_docs(
        request: Request,
        session: AsyncSession = Depends(get_session),
        _config=config,
        _base_url=base_url,
    ):
        docs = await doc_service.list_docs(session, doc_types=_config["doc_types"])
        return templates.TemplateResponse("docs_page.html", {
            "request": request,
            "docs": docs,
            "base_url": _base_url,
            **_config,
        })

    # Create doc
    @router.post(base_url, name=f"create_{section_key.replace('-', '_')}")
    async def create_doc(
        filename: str = Form(...),
        display_name: str = Form(...),
        content: str = Form(...),
        doc_type: str = Form(config["default_type"]),
        session: AsyncSession = Depends(get_session),
        _base_url=base_url,
    ):
        data = ProductDocCreate(
            filename=filename,
            display_name=display_name,
            content=content,
            doc_type=doc_type,
        )
        await doc_service.create_doc(session, data)
        return RedirectResponse(_base_url, status_code=303)

    # Edit form
    @router.get(f"{base_url}/{{doc_id}}/edit", response_class=HTMLResponse, name=f"edit_{section_key.replace('-', '_')}_form")
    async def edit_doc_form(
        request: Request,
        doc_id: UUID,
        session: AsyncSession = Depends(get_session),
        _config=config,
        _base_url=base_url,
    ):
        doc = await doc_service.get_doc(session, doc_id)
        if not doc:
            return HTMLResponse("<h2>Document not found</h2>", status_code=404)
        return templates.TemplateResponse("docs_edit.html", {
            "request": request,
            "doc": doc,
            "base_url": _base_url,
            "active_page": _config["active_page"],
            "type_options": _config["type_options"],
        })

    # Update doc
    @router.post(f"{base_url}/{{doc_id}}/edit", name=f"update_{section_key.replace('-', '_')}")
    async def update_doc(
        doc_id: UUID,
        display_name: str = Form(...),
        content: str = Form(...),
        doc_type: str = Form(config["default_type"]),
        session: AsyncSession = Depends(get_session),
        _base_url=base_url,
    ):
        data = ProductDocUpdate(display_name=display_name, content=content, doc_type=doc_type)
        await doc_service.update_doc(session, doc_id, data)
        return RedirectResponse(_base_url, status_code=303)

    # Toggle active
    @router.post(f"{base_url}/{{doc_id}}/toggle", name=f"toggle_{section_key.replace('-', '_')}")
    async def toggle_doc(
        doc_id: UUID,
        session: AsyncSession = Depends(get_session),
        _base_url=base_url,
    ):
        doc = await doc_service.get_doc(session, doc_id)
        if doc:
            data = ProductDocUpdate(is_active=not doc.is_active)
            await doc_service.update_doc(session, doc_id, data)
        return RedirectResponse(_base_url, status_code=303)

    # Delete
    @router.post(f"{base_url}/{{doc_id}}/delete", name=f"delete_{section_key.replace('-', '_')}")
    async def delete_doc(
        doc_id: UUID,
        session: AsyncSession = Depends(get_session),
        _base_url=base_url,
    ):
        await doc_service.delete_doc(session, doc_id)
        return RedirectResponse(_base_url, status_code=303)
