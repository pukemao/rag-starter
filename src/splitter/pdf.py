"""PDF-aware section builders for RAG chunking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from langchain_core.documents import Document

from .base import SplitterDependencyError

_PDF_FILETYPE = "application/pdf"
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PAGE_SEPARATOR_PATTERN = re.compile(r"^-{3,}\s*end of page=.*?-{3,}$", re.IGNORECASE)
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\([^)]+\)")
_CJK_PATTERN = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"


@dataclass(frozen=True, slots=True)
class PdfPage:
    """Normalized PDF page content."""

    page_number: int
    text: str
    metadata: dict[str, Any]
    toc_items: list[Any]
    tables: list[Any]


def split_pdf_file(
    file_path: str | Path,
    *,
    splitter: Any | None = None,
    splitter_type: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **splitter_kwargs: Any,
) -> list[Document]:
    """Split a PDF into heading-aware, retrieval-friendly chunks."""

    from .registry import split_documents

    sections = build_pdf_sections(file_path)
    chunks = split_documents(
        sections,
        splitter=splitter,
        splitter_type=splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **splitter_kwargs,
    )
    return [ensure_pdf_heading_context(chunk) for chunk in chunks]


def build_pdf_sections(file_path: str | Path) -> list[Document]:
    """Extract PDF pages as Markdown and group them into semantic sections."""

    path = Path(file_path)
    pages = _extract_pdf_pages(path)
    pages = _remove_repeated_page_edges(pages)
    sections = build_pdf_sections_from_pages(path, pages)
    if sections:
        return sections
    return [_empty_pdf_document(path)]


def build_pdf_sections_from_pages(path: Path, pages: list[PdfPage]) -> list[Document]:
    """Build heading-aware section documents from normalized PDF pages."""

    sections: list[Document] = []
    heading_stack: dict[int, str] = {}
    current_lines: list[str] = []
    current_pages: list[int] = []
    current_tables = 0
    current_has_body = False
    current_heading_level: int | None = None

    def reset_current() -> None:
        nonlocal current_lines, current_pages, current_tables, current_has_body, current_heading_level
        current_lines = _heading_lines(heading_stack)
        current_pages = []
        current_tables = 0
        current_has_body = False
        current_heading_level = max(heading_stack) if heading_stack else None

    def flush() -> None:
        nonlocal current_lines, current_pages, current_tables, current_has_body, current_heading_level
        text = "\n\n".join(_dedupe_consecutive_lines(line for line in current_lines if line.strip())).strip()
        if not text:
            return
        sections.append(
            Document(
                page_content=text,
                metadata=_pdf_metadata(
                    path,
                    heading_stack,
                    pages=current_pages,
                    table_count=current_tables,
                ),
            )
        )
        current_lines = []
        current_pages = []
        current_tables = 0
        current_has_body = False
        current_heading_level = None

    for page in pages:
        lines = _clean_pdf_markdown(page.text).splitlines()
        if page.tables:
            current_tables += len(page.tables)
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            match = _HEADING_PATTERN.match(line)
            if match:
                if current_lines and current_has_body:
                    flush()
                level = max(1, min(len(match.group(1)), 6))
                heading = _plain_heading(match.group(2))
                _apply_heading(heading_stack, level, heading, previous_level=current_heading_level, previous_has_body=current_has_body)
                reset_current()
                _add_page(current_pages, page.page_number)
                continue

            if not current_lines:
                reset_current()
            current_lines.append(line)
            _add_page(current_pages, page.page_number)
            current_has_body = True

    if current_lines:
        flush()

    if not sections:
        return []

    if not any(section.metadata.get("heading_context") for section in sections):
        return _merge_unheaded_sections(path, sections)

    return sections


def ensure_pdf_heading_context(document: Document) -> Document:
    """Prefix heading context to split chunks that lost it."""

    heading_context = str(document.metadata.get("heading_context") or "").strip()
    if not heading_context:
        return document

    content = document.page_content.strip()
    if _has_heading_prefix(content, heading_context):
        return document

    return Document(
        page_content=f"{heading_context}\n\n{content}",
        metadata=dict(document.metadata),
    )


def _extract_pdf_pages(path: Path) -> list[PdfPage]:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise SplitterDependencyError("无法导入 pymupdf4llm。请安装依赖: pip install pymupdf4llm") from exc

    raw_pages = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        header=False,
        footer=False,
        write_images=False,
        embed_images=False,
        ignore_images=True,
        force_text=True,
        page_separators=False,
        show_progress=False,
        table_strategy="lines_strict",
    )
    pages: list[PdfPage] = []
    for index, raw_page in enumerate(raw_pages if isinstance(raw_pages, list) else [], start=1):
        metadata = dict(raw_page.get("metadata") or {})
        page_number = _as_int(metadata.get("page_number"), index)
        pages.append(
            PdfPage(
                page_number=page_number,
                text=str(raw_page.get("text") or ""),
                metadata=metadata,
                toc_items=list(raw_page.get("toc_items") or []),
                tables=list(raw_page.get("tables") or []),
            )
        )
    return pages


def _remove_repeated_page_edges(pages: list[PdfPage]) -> list[PdfPage]:
    candidates: dict[str, int] = {}
    for page in pages:
        lines = [line.strip() for line in _clean_pdf_markdown(page.text).splitlines() if line.strip()]
        for line in [*lines[:3], *lines[-3:]]:
            normalized = _edge_key(line)
            if normalized:
                candidates[normalized] = candidates.get(normalized, 0) + 1

    threshold = max(2, len(pages) // 2 + 1)
    repeated = {line for line, count in candidates.items() if count >= threshold}
    if not repeated:
        return pages

    cleaned_pages = []
    for page in pages:
        lines = _clean_pdf_markdown(page.text).splitlines()
        cleaned = []
        for index, line in enumerate(lines):
            is_edge = index < 3 or index >= len(lines) - 3
            if is_edge and _edge_key(line) in repeated:
                continue
            cleaned.append(line)
        cleaned_pages.append(
            PdfPage(
                page_number=page.page_number,
                text="\n".join(cleaned),
                metadata=page.metadata,
                toc_items=page.toc_items,
                tables=page.tables,
            )
        )
    return cleaned_pages


def _merge_unheaded_sections(path: Path, sections: list[Document]) -> list[Document]:
    lines: list[str] = [f"# {path.stem}"]
    pages: list[int] = []
    table_count = 0
    for section in sections:
        content = section.page_content.strip()
        if content:
            lines.append(content)
        pages.extend(_metadata_pages(section.metadata))
        table_count += _as_int(section.metadata.get("table_count"), 0)
    return [
        Document(
            page_content="\n\n".join(lines).strip(),
            metadata=_pdf_metadata(
                path,
                {1: path.stem},
                pages=pages,
                table_count=table_count,
            ),
        )
    ]


def _clean_pdf_markdown(text: str) -> str:
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = _IMAGE_PATTERN.sub("", text)
    lines: list[str] = []
    last_blank = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if _PAGE_SEPARATOR_PATTERN.match(line):
            continue
        line = _normalize_cjk_spacing(line)
        if not line:
            if not last_blank:
                lines.append("")
            last_blank = True
            continue
        lines.append(line)
        last_blank = False
    return "\n".join(lines).strip()


def _dedupe_consecutive_lines(lines: list[str] | tuple[str, ...] | Any) -> list[str]:
    deduped: list[str] = []
    previous: str | None = None
    for line in lines:
        current = str(line).strip()
        if not current:
            continue
        if current == previous:
            continue
        deduped.append(current)
        previous = current
    return deduped


def _normalize_cjk_spacing(text: str) -> str:
    text = re.sub(rf"(?<=[{_CJK_PATTERN}])\s+(?=[{_CJK_PATTERN}])", "", text)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    text = re.sub(rf"(?<=\d)\s+(?=[{_CJK_PATTERN}])", "", text)
    text = re.sub(rf"(?<=[{_CJK_PATTERN}])\s+(?=\d)", "", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _edge_key(line: str) -> str:
    line = _normalize_cjk_spacing(line)
    line = re.sub(r"\d+", "#", line)
    line = re.sub(r"\s+", " ", line).strip()
    if len(line) < 4:
        return ""
    return line


def _plain_heading(text: str) -> str:
    text = re.sub(r"[*_`]+", "", text)
    return _normalize_cjk_spacing(text).strip()


def _heading_lines(heading_stack: dict[int, str]) -> list[str]:
    return [f"{'#' * level} {heading_stack[level]}" for level in sorted(heading_stack)]


def _apply_heading(
    heading_stack: dict[int, str],
    level: int,
    heading: str,
    *,
    previous_level: int | None,
    previous_has_body: bool,
) -> None:
    if previous_level == level and not previous_has_body and heading_stack.get(level):
        level = min(level + 1, 6)
    for existing_level in list(heading_stack):
        if existing_level >= level:
            heading_stack.pop(existing_level)
    heading_stack[level] = heading


def _pdf_metadata(
    path: Path,
    heading_stack: dict[int, str],
    *,
    pages: list[int],
    table_count: int,
) -> dict[str, Any]:
    unique_pages = sorted({page for page in pages if page > 0})
    metadata: dict[str, Any] = {
        "source": str(path),
        "filename": path.name,
        "filetype": _PDF_FILETYPE,
        "chunk_type": "pdf_section",
        "table_count": table_count,
    }
    if unique_pages:
        metadata["page_start"] = unique_pages[0]
        metadata["page_end"] = unique_pages[-1]
        metadata["pages"] = ",".join(str(page) for page in unique_pages)
    heading_lines = _heading_lines(heading_stack)
    if heading_lines:
        metadata["heading_context"] = "\n".join(heading_lines)
    for level, heading in heading_stack.items():
        metadata[f"h{level}"] = heading
    return metadata


def _metadata_pages(metadata: dict[str, Any]) -> list[int]:
    pages = metadata.get("pages")
    if isinstance(pages, str):
        return [_as_int(page, 0) for page in pages.split(",") if page.strip()]
    if metadata.get("page_start") and metadata.get("page_end"):
        return list(range(_as_int(metadata["page_start"], 0), _as_int(metadata["page_end"], 0) + 1))
    return []


def _empty_pdf_document(path: Path) -> Document:
    return Document(
        page_content=f"# {path.stem}",
        metadata={
            "source": str(path),
            "filename": path.name,
            "filetype": _PDF_FILETYPE,
            "chunk_type": "pdf_section",
        },
    )


def _add_page(pages: list[int], page_number: int) -> None:
    if page_number > 0:
        pages.append(page_number)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _has_heading_prefix(content: str, heading_context: str) -> bool:
    content_lines = [line.strip() for line in content.splitlines() if line.strip()]
    heading_lines = [line.strip() for line in heading_context.splitlines() if line.strip()]
    if not heading_lines or len(content_lines) < len(heading_lines):
        return False
    return content_lines[: len(heading_lines)] == heading_lines
