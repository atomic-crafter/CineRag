from pathlib import Path

from pptx import Presentation
from pypdf import PdfReader


def load_pdf(file_path: str) -> list[tuple[int, str]]:
    """Returns a list of (page_number, text), 1-indexed pages."""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def load_pptx(file_path: str) -> list[tuple[int, str]]:
    """Returns a list of (slide_number, text), 1-indexed slides."""
    prs = Presentation(file_path)
    slides = []
    for i, slide in enumerate(prs.slides, start=1):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                if text.strip():
                    parts.append(text)
        text = "\n".join(parts)
        if text.strip():
            slides.append((i, text))
    return slides


def load_document(file_path: str) -> list[tuple[int, str]]:
    """Dispatches on file extension. Returns list of (page_number, text)."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    if ext in (".ppt", ".pptx"):
        return load_pptx(file_path)
    raise ValueError(f"Unsupported file extension: {ext}")
