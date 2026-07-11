"""Best-effort text extraction for content search.

Never raises -- a failed or unsupported extraction just means the file
won't show up in content-search results, not a broken upload/import.
"""
import logging

logger = logging.getLogger(__name__)

# Caps stored text so a huge PDF doesn't bloat the DB row or the search index.
_MAX_CHARS = 200_000

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def extract_text(file_path: str, mime_type: str) -> str | None:
    try:
        if mime_type == "text/plain":
            return _extract_txt(file_path)
        if mime_type == "application/pdf":
            return _extract_pdf(file_path)
        if mime_type == _DOCX_MIME:
            return _extract_docx(file_path)
    except Exception:
        logger.warning(
            "Text extraction failed for %s (%s)", file_path, mime_type, exc_info=True
        )
    return None


def _extract_txt(file_path: str) -> str | None:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        text = fh.read(_MAX_CHARS)
    return text or None


def _extract_pdf(file_path: str) -> str | None:
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    chunks = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
        total += len(text)
        if total >= _MAX_CHARS:
            break
    joined = "\n".join(chunks)[:_MAX_CHARS]
    return joined or None


def _extract_docx(file_path: str) -> str | None:
    from docx import Document

    doc = Document(file_path)
    text = "\n".join(p.text for p in doc.paragraphs)[:_MAX_CHARS]
    return text or None
