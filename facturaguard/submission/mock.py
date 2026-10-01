"""Mock ANAF adapter: simulates an upload with our own validator. Nothing leaves the server."""

import hashlib

from facturaguard.submission.base import SubmissionResult
from facturaguard.validation.validate import validate_xml


class MockAnafAdapter:
    def __init__(self):
        self._uploads: dict[str, SubmissionResult] = {}

    def submit(self, xml: bytes, seller_cif: str) -> SubmissionResult:
        index = str(int(hashlib.sha256(xml).hexdigest()[:12], 16) % 10**10).zfill(10)
        result = validate_xml(xml)
        if any(i.layer in ("parse", "xsd") for i in result.issues):
            out = SubmissionResult(index, "XML cu erori nepreluat de sistem",
                                   "MOCK: the XML is not schema-valid, so ANAF would not even "
                                   "accept the upload.",
                                   sorted({i.rule_id for i in result.issues}))
        elif result.valid:
            out = SubmissionResult(index, "ok", f"MOCK: invoice accepted for seller {seller_cif}. "
                                   "A real upload would return an index to poll and, later, a "
                                   "signed response from ANAF.")
        else:
            out = SubmissionResult(index, "nok", "MOCK: ANAF would reject the invoice after "
                                   "processing it.",
                                   sorted({i.rule_id for i in result.issues
                                           if i.severity == "fatal"}))
        self._uploads[index] = out
        return out

    def status(self, upload_index: str) -> SubmissionResult:
        return self._uploads.get(upload_index) or SubmissionResult(
            upload_index, "nok", "MOCK: unknown upload index.")
