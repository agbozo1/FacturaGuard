"""Apply model-proposed edit operations to an invoice deterministically.

The model never returns a whole new XML document. It returns a short list of operations, each
addressing exactly one node by XPath. Anything ambiguous is rejected, not guessed.

Operations:
  {"op": "set_text", "xpath": ..., "value": ...}
  {"op": "set_attribute", "xpath": ..., "name": ..., "value": ...}
  {"op": "delete", "xpath": ...}
  {"op": "insert_after" | "insert_before", "xpath": <existing sibling>, "xml": <fragment>}
  {"op": "append_child", "xpath": <parent>, "xml": <fragment>}
XPath prefixes: ubl (Invoice), cn (CreditNote), cac, cbc.
"""

import difflib
from dataclasses import dataclass, field

from lxml import etree

NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cn": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
OPS = {"set_text", "set_attribute", "delete", "insert_after", "insert_before", "append_child"}


class PatchError(ValueError):
    pass


@dataclass
class PatchOutcome:
    xml: bytes
    applied: list[dict] = field(default_factory=list)
    rejected: list[tuple[dict, str]] = field(default_factory=list)


def _one(root, xpath: str):
    try:
        nodes = root.xpath(xpath, namespaces=NS)
    except etree.XPathError as e:
        raise PatchError(f"invalid XPath: {e}") from e
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], etree._Element):
        n = len(nodes) if isinstance(nodes, list) else "a non-node"
        raise PatchError(f"XPath must select exactly one element, got {n}")
    return nodes[0]


def _fragment(xml: str) -> list:
    decls = " ".join(f'xmlns:{p}="{u}"' for p, u in NS.items() if p in ("cac", "cbc"))
    try:
        wrapper = etree.fromstring(f"<wrap {decls}>{xml}</wrap>".encode())
    except etree.XMLSyntaxError as e:
        raise PatchError(f"fragment is not well-formed: {e}") from e
    kids = list(wrapper)
    if not kids:
        raise PatchError("fragment has no element")
    return kids


def _apply_one(root, op: dict) -> None:
    kind = op.get("op")
    if kind not in OPS:
        raise PatchError(f"unknown op {kind!r}")
    target = _one(root, op.get("xpath", ""))
    if kind == "set_text":
        if len(target):
            raise PatchError("set_text target has child elements")
        target.text = str(op.get("value", ""))
    elif kind == "set_attribute":
        target.set(str(op["name"]), str(op.get("value", "")))
    elif kind == "delete":
        if target.getparent() is None:
            raise PatchError("cannot delete the root element")
        target.getparent().remove(target)
    elif kind == "append_child":
        for el in _fragment(op.get("xml", "")):
            target.append(el)
    else:
        parent = target.getparent()
        if parent is None:
            raise PatchError("cannot insert next to the root element")
        idx = parent.index(target) + (1 if kind == "insert_after" else 0)
        for offset, el in enumerate(_fragment(op.get("xml", ""))):
            parent.insert(idx + offset, el)


def apply_ops(xml: bytes, ops: list[dict]) -> PatchOutcome:
    """Apply ops one by one; a failing op is rejected and the others still apply."""
    root = etree.fromstring(xml)
    outcome = PatchOutcome(xml=xml)
    for op in ops:
        snapshot = etree.tostring(root)
        try:
            _apply_one(root, op)
            outcome.applied.append(op)
        except (PatchError, KeyError, TypeError) as e:
            root = etree.fromstring(snapshot)
            outcome.rejected.append((op, str(e)))
    etree.indent(root, space="  ")
    outcome.xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8") + b"\n"
    return outcome


def unified_diff(before: bytes, after: bytes) -> str:
    def norm(b: bytes) -> list[str]:
        root = etree.fromstring(b)
        etree.indent(root, space="  ")
        return etree.tostring(root, encoding="unicode").splitlines(keepends=True)

    return "".join(difflib.unified_diff(norm(before), norm(after), "original.xml", "corrected.xml"))
