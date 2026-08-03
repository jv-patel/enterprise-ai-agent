"""Extracts plain text from uploaded documents (PDF, DOCX, TXT, CSV, XLSX/XLS)."""
import csv
import io

import openpyxl
from docx import Document
from pypdf import PdfReader

from app.core.exceptions import ValidationAppError

SUPPORTED_TYPES = {"pdf", "docx", "txt", "csv", "xlsx", "xls"}

_MAX_ROWS = 2000


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _extract_csv(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)[:_MAX_ROWS]
    return "\n".join(", ".join(cell for cell in row) for row in rows)


def _extract_xlsx(content: bytes) -> str:
    workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        lines.append(f"# Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True, max_row=_MAX_ROWS):
            lines.append(", ".join("" if cell is None else str(cell) for cell in row))
    return "\n".join(lines)


def extract_text(*, content: bytes, file_type: str) -> str:
    normalized_type = file_type.lower().lstrip(".")
    if normalized_type not in SUPPORTED_TYPES:
        raise ValidationAppError(f"Unsupported document type: {normalized_type}", error_code="unsupported_file_type")

    if normalized_type == "pdf":
        return _extract_pdf(content)
    if normalized_type == "docx":
        return _extract_docx(content)
    if normalized_type == "txt":
        return _extract_txt(content)
    if normalized_type == "csv":
        return _extract_csv(content)
    return _extract_xlsx(content)  # xlsx or xls
