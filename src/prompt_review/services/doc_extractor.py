"""
Extract text content from uploaded document files.

Supported formats: .pdf, .txt, .md, .docx
The extracted text is stored in the database; the original file is not saved.
"""
import io
import logging

logger = logging.getLogger(__name__)

ACCEPTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
ACCEPTED_TYPES_DISPLAY = ".pdf, .txt, .md, .docx"


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract plain text from an uploaded file.

    Args:
        filename: Original filename (used to determine format).
        file_bytes: Raw file content.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the file type is not supported or extraction fails.
    """
    ext = _get_extension(filename)

    if ext not in ACCEPTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Accepted: {ACCEPTED_TYPES_DISPLAY}")

    if ext in (".txt", ".md"):
        return _extract_text_plain(file_bytes)
    elif ext == ".pdf":
        return _extract_text_pdf(file_bytes)
    elif ext == ".docx":
        return _extract_text_docx(file_bytes)

    raise ValueError(f"No extractor for '{ext}'")


def _get_extension(filename: str) -> str:
    """Get lowercase file extension."""
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()


def _extract_text_plain(file_bytes: bytes) -> str:
    """Extract text from plain text or markdown files."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file (tried utf-8, latin-1)")


def _extract_text_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    if not pages:
        raise ValueError("PDF contains no extractable text (may be image-only)")

    return "\n\n".join(pages)


def _extract_text_docx(file_bytes: bytes) -> str:
    """Extract text from a Word .docx file."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError("Word document contains no text")

    return "\n\n".join(paragraphs)
