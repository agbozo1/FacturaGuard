"""Read scanned invoices (image-only PDFs, JPG, PNG) with a vision model on Token Factory.

No Nemotron vision model was available on our key, so this one step uses MiniCPM-V
(`MODEL_VISION`). It only transcribes the page to text; Nemotron Lightning then extracts the
fields from that text exactly as for a text PDF. Because the transcription is the only text we can
check against, every value read from a scan is presented as "please verify".
"""

import base64
import io
import re

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from facturaguard.llm.ask import CallRecord
from facturaguard.llm.client import LLMClient
from facturaguard.validation.cui import cui_is_valid

MAX_PAGES = 3
MAX_SIDE = 1800      # long side sent to the model: enough for invoice text, keeps calls fast
PREVIEW_WIDTH = 900
MIN_CHARS = 40

TRANSCRIBE_PROMPT = (
    "Transcribe all text on this invoice image exactly as printed, line by line, top to bottom. "
    "Keep every number, code and punctuation exactly as shown (Romanian number format like "
    "1.234,56 stays as printed). For tables, write one row per line with cells separated by "
    "' | '. Do not summarise, correct, translate or add anything."
)


class ScanError(ValueError):
    pass


def is_image(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"


def _normalise(img: Image.Image) -> bytes:
    img = img.convert("L") if img.mode in ("1", "L", "LA", "P", "I;16") else img.convert("RGB")
    scale = MAX_SIDE / max(img.size)
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def page_images(data: bytes) -> list[bytes]:
    """JPEG bytes for each page (up to MAX_PAGES) of a scanned PDF, or for a single image."""
    try:
        if is_image(data):
            return [_normalise(Image.open(io.BytesIO(data)))]
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages[:MAX_PAGES]:
            imgs = list(page.images)
            if imgs:  # a scan page is one large image; take the biggest
                biggest = max(imgs, key=lambda i: i.image.width * i.image.height)
                pages.append(_normalise(biggest.image))
    except (PdfReadError, UnidentifiedImageError, OSError, ValueError) as e:
        raise ScanError(f"Could not read the image: {e}") from e
    if not pages:
        raise ScanError("This PDF has no text and no readable image. Try uploading a JPG or PNG "
                        "photo of the invoice instead.")
    return pages


def preview_data_url(jpeg: bytes) -> str:
    img = Image.open(io.BytesIO(jpeg))
    if img.width > PREVIEW_WIDTH:
        img = img.resize((PREVIEW_WIDTH, round(img.height * PREVIEW_WIDTH / img.width)),
                         Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _strip_html(text: str) -> str:
    """Some vision models answer tables as HTML; turn rows into 'a | b | c' lines."""
    if "<td" not in text and "<tr" not in text:
        return text
    text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n\s*\n+", "\n", text)


def transcribe(pages: list[bytes], llm: LLMClient, calls: list[CallRecord],
               role: str = "vision") -> str:
    texts = []
    for n, jpeg in enumerate(pages, 1):
        url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
        res = llm.chat(role, [{"role": "user", "content": [
            {"type": "text", "text": TRANSCRIBE_PROMPT},
            {"type": "image_url", "image_url": {"url": url}},
        ]}], max_tokens=4000, temperature=0)
        calls.append(CallRecord("transcribe", res.model, round(res.latency_s, 2),
                                res.prompt_tokens, res.completion_tokens, ok=bool(res.text)))
        texts.append(f"--- page {n} ---\n{_strip_html(res.text)}" if len(pages) > 1
                     else _strip_html(res.text))
    text = "\n".join(texts)
    if len("".join(text.split())) < MIN_CHARS:
        raise ScanError("No readable text was found on the scan. Try a sharper, straight photo.")
    return text


def iban_is_valid(iban: str) -> bool:
    s = re.sub(r"\s+", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", s):
        return False
    return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1


def _romanian(p: dict) -> bool:
    country = (p.get("country") or "").strip().casefold()
    return country in ("ro", "romania", "românia") or (
        not country and (p.get("vat_id") or "").upper().startswith("RO"))


def scan_suspects(fields: dict) -> list[dict]:
    """Values whose built-in check fails: on a scan, most likely a misread digit.

    Grounding cannot catch a misread (the transcription is the only text we have), but IBANs
    (mod 97), CUIs (control digit) and Romanian postal codes (6 digits) can check themselves.
    """
    out = []
    for role in ("seller", "buyer"):
        p = fields.get(role) or {}
        iban = p.get("iban")
        if iban and not iban_is_valid(iban):
            out.append({"field": f"{role}.iban", "value": iban,
                        "reason": "IBAN check digits do not match"})
        if not _romanian(p):
            continue
        vat = re.sub(r"\s+", "", p.get("vat_id") or "").upper()
        if re.fullmatch(r"(RO)?\d{2,10}", vat) and not cui_is_valid(vat):
            out.append({"field": f"{role}.vat_id", "value": p["vat_id"],
                        "reason": "CUI control digit does not match"})
        postal = (p.get("postal_code") or "").strip()
        if postal and not re.fullmatch(r"\d{6}", postal):
            out.append({"field": f"{role}.postal_code", "value": postal,
                        "reason": "Romanian postal codes have 6 digits"})
    return out
