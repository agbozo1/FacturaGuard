import json
from pathlib import Path

import pytest

from facturaguard.validation.validate import validate_xml

ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
MANIFEST = json.loads((ROOT / "manifest.json").read_text())["invoices"]


@pytest.fixture(scope="module")
def results():
    return {e["id"]: validate_xml((ROOT / e["file"]).read_bytes()) for e in MANIFEST}


def test_designed_valid_invoices_pass_with_no_issues(results):
    for e in MANIFEST:
        if e["designed_valid"]:
            assert results[e["id"]].issues == [], e["id"]


def test_every_expected_rule_fires(results):
    for e in MANIFEST:
        fired = {i.rule_id for i in results[e["id"]].issues if i.severity == "fatal"}
        assert set(e["expected_rules"]) <= fired, (e["id"], e["mutations"], fired)


def test_every_broken_invoice_is_rejected(results):
    for e in MANIFEST:
        if not e["designed_valid"]:
            assert not results[e["id"]].valid, (e["id"], e["mutations"])


def test_xsd_and_parse_layers_are_reported(results):
    for e in MANIFEST:
        layers = {i.layer for i in results[e["id"]].issues}
        for layer in ("xsd", "parse"):
            if layer in e["layers"]:
                assert layer in layers, (e["id"], e["mutations"])


def test_not_xml_and_wrong_root():
    assert validate_xml(b"not xml").issues[0].layer == "parse"
    r = validate_xml(b"<a/>")
    assert not r.valid and r.issues[0].rule_id == "XSD-ROOT"
