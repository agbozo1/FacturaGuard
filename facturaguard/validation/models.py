from dataclasses import asdict, dataclass, field
from typing import Literal

Layer = Literal["parse", "xsd", "schematron", "anaf_identifier"]


@dataclass
class Issue:
    layer: Layer
    rule_id: str
    severity: Literal["fatal", "warning"]
    message: str
    location: str = ""
    test: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationResult:
    kind: str = "unknown"  # Invoice | CreditNote | unknown
    issues: list[Issue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(i.severity == "fatal" for i in self.issues)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "kind": self.kind, "issues": [i.to_dict() for i in self.issues]}
