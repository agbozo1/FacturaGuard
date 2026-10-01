"""Text layer of a PDF. Scanned (image-only) PDFs are out of scope: no Nemotron vision model was
available on our Token Factory key, so they are reported instead of guessed."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIN_TEXT_CHARS = 80
MAX_PAGES = 10


class PdfTextError(ValueError):
    pass


def extract_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except (PdfReadError, ValueError) as e:
        raise PdfTextError(f"Could not read the PDF: {e}") from e
    if len("".join(text.split())) < MIN_TEXT_CHARS:
        raise PdfTextError(
            "The PDF has no readable text layer (it is probably a scan). FacturaGuard reads "
            "text-based PDFs exported from invoicing software; scans are not supported yet."
        )
    return text
