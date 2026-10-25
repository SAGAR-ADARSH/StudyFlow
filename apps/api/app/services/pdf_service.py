"""PDF validation and text extraction built on PyMuPDF.

Extraction is intentionally defensive: a corrupt file, an empty document and a
scanned document with no text layer all raise :class:`PdfProcessingError` with a
stable ``code`` so the API can store the failure and show the student a
meaningful message instead of marking the document as processed.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

try:  # PyMuPDF >= 1.24 exposes the modern module name.
    import pymupdf as fitz
except ImportError:  # pragma: no cover - fallback for older installs
    import fitz  # type: ignore[no-redef]

PDF_MAGIC = b"%PDF-"
PDF_CONTENT_TYPE = "application/pdf"
# Long enough to build a summary/quiz from; shorter than this is treated as noise.
MIN_EXTRACTED_CHARS = 120
# Guard rail so a 400-page textbook cannot blow past MEDIUMTEXT.
MAX_STORED_CHARS = 400_000


class PdfProcessingError(Exception):
    """A PDF could not be turned into usable text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class ExtractionResult:
    text: str
    page_count: int
    page_offsets: list[int] = field(default_factory=list)
    char_count: int = 0
    word_count: int = 0
    truncated: bool = False
    has_images: bool = False


def looks_like_pdf(data: bytes) -> bool:
    """True when the payload carries the PDF magic bytes."""
    return bool(data) and data[: len(PDF_MAGIC)] == PDF_MAGIC


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(data: bytes) -> ExtractionResult:
    """Extract the text layer of a PDF, raising :class:`PdfProcessingError`."""
    if not looks_like_pdf(data):
        raise PdfProcessingError(
            "invalid_pdf",
            "That file is not a PDF. Please upload a document saved as .pdf.",
        )

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as error:  # PyMuPDF raises many C-level error types
        raise PdfProcessingError(
            "corrupt_pdf",
            "The PDF could not be opened; it looks corrupted or password protected.",
        ) from error

    try:
        page_count = document.page_count
        if page_count == 0:
            raise PdfProcessingError(
                "empty_document",
                "This PDF has no pages, so there is nothing to summarise or quiz.",
            )

        if document.needs_pass:
            raise PdfProcessingError(
                "password_protected",
                "This PDF is password protected. Remove the password and upload it again.",
            )

        chunks: list[str] = []
        page_offsets: list[int] = []
        has_images = False
        cursor = 0
        for page in document:
            page_text = _normalize(page.get_text("text"))
            page_offsets.append(cursor)
            if page_text:
                chunks.append(page_text)
                cursor += len(page_text) + 2
            if not has_images:
                try:
                    has_images = bool(page.get_images(full=True))
                except Exception:  # noqa: BLE001 - image probing is best effort
                    has_images = False
    except PdfProcessingError:
        raise
    except Exception as error:
        raise PdfProcessingError(
            "extraction_failed",
            "Text extraction failed while reading this PDF.",
        ) from error
    finally:
        document.close()

    text = _normalize("\n\n".join(chunks))
    if len(text) > MAX_STORED_CHARS:
        text = text[:MAX_STORED_CHARS].rsplit(" ", 1)[0]
        truncated = True
    else:
        truncated = False

    char_count = len(text)
    if char_count == 0:
        if has_images:
            raise PdfProcessingError(
                "scanned_pdf",
                "This looks like a scanned/image-only PDF with no selectable text layer. "
                "StudyFlow extracts text directly; OCR is not installed. "
                "To use this material: (1) export a text-based PDF from Word/Google Docs, or (2) run a local OCR tool "
                "(e.g., open-source OCRmyPDF with Tesseract) to add a text layer, then re-upload.",
            )
        raise PdfProcessingError(
            "empty_document",
            "No text could be extracted from this PDF. The file may contain only images or be blank. "
            "Try exporting a text-based version or using a local OCR tool to add a text layer.",
        )
    if char_count < MIN_EXTRACTED_CHARS:
        raise PdfProcessingError(
            "insufficient_text",
            f"Only {char_count} characters of text were found, which is too little to "
            "summarise or build questions from.",
        )

    return ExtractionResult(
        text=text,
        page_count=page_count,
        page_offsets=page_offsets,
        char_count=char_count,
        word_count=len(text.split()),
        truncated=truncated,
        has_images=has_images,
    )


async def extract_pdf_text_async(data: bytes) -> ExtractionResult:
    """Run extraction off the event loop so uploads never block the API."""
    return await asyncio.to_thread(extract_pdf_text, data)
