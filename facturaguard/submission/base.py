"""Submission interface. Live ANAF submission (OAuth, SPV upload, polling) is out of scope;
the app uses MockAnafAdapter. A real adapter would implement the same two methods."""

from dataclasses import asdict, dataclass, field
from typing import Literal, Protocol

# Mirrors the states ANAF's e-Factura API reports for an upload.
Status = Literal["in prelucrare", "ok", "nok", "XML cu erori nepreluat de sistem"]


@dataclass
class SubmissionResult:
    upload_index: str
    status: Status
    message: str
    errors: list[str] = field(default_factory=list)
    mock: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class SubmissionAdapter(Protocol):
    def submit(self, xml: bytes, seller_cif: str) -> SubmissionResult: ...

    def status(self, upload_index: str) -> SubmissionResult: ...
