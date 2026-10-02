"""Text layer of a PDF. Image-only PDFs (scans) raise NoTextLayer so the pipeline can send them to
the scan reader (facturaguard/extraction/scan.py) instead."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIN_TEXT_CHARS = 80
MAX_PAGES = 10


class PdfTextError(ValueError):
    pass


class NoTextLayer(PdfTextError):
    """A readable PDF with (almost) no text: most likely a scan or a photo saved as PDF."""


def extract_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except (PdfReadError, ValueError) as e:
        raise PdfTextError(f"Could not read the PDF: {e}") from e
    if len("".join(text.split())) < MIN_TEXT_CHARS:
        raise NoTextLayer(
            "The PDF has no readable text layer (it is probably a scan), and scan reading is not "
            "configured on this server. Upload the PDF exported from your invoicing software."
        )
    return text
