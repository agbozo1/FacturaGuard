import json
import random
import re
from decimal import Decimal

import pytest
from lxml import etree

from facturaguard.synthetic.generate import generate
from facturaguard.synthetic.identifiers import corrupt_cui, cui_is_valid, make_cui, make_iban
from facturaguard.synthetic.mutations import BY_NAME, MUTATIONS

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "i": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
}


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    path = tmp_path_factory.mktemp("syn")
    generate(path, 2026)
    return path


def test_cui_checksum_roundtrip():
    rng = random.Random(1)
    for _ in range(200):
        cui = make_cui(rng)
        assert cui_is_valid(cui)
        assert not cui_is_valid(corrupt_cui(cui))


def test_iban_mod97():
    iban = make_iban(random.Random(1))
    moved = iban[4:] + iban[:4]
    assert int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


def test_set_size_and_manifest(out):
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["count"] == len(manifest["invoices"]) == 100
    assert len(list((out / "xml").glob("*.xml"))) == 100
    assert any(e["designed_valid"] for e in manifest["invoices"])
    for e in manifest["invoices"]:
        assert all(re.fullmatch(r"BR-[A-Z]{0,3}-?\d{2,3}", r) for r in e["expected_rules"])
        assert e["designed_valid"] == (not e["mutations"])


def test_every_mutation_is_used(out):
    manifest = json.loads((out / "manifest.json").read_text())
    used = {m for e in manifest["invoices"] for m in e["mutations"]}
    assert used == set(BY_NAME) and len(MUTATIONS) == len(BY_NAME)


def test_deterministic(out, tmp_path):
    generate(tmp_path, 2026)
    for f in (out / "xml").glob("*.xml"):
        assert f.read_text() == (tmp_path / "xml" / f.name).read_text()


def test_wellformedness_matches_labels(out):
    manifest = json.loads((out / "manifest.json").read_text())
    for e in manifest["invoices"]:
        data = (out / e["file"]).read_bytes()
        if "malformed_xml" in e["mutations"]:
            with pytest.raises(etree.XMLSyntaxError):
                etree.fromstring(data)
        else:
            etree.fromstring(data)


def _n(root, path):
    return Decimal(root.xpath(path, namespaces=NS)[0].text)


def test_valid_invoices_are_arithmetically_consistent(out):
    manifest = json.loads((out / "manifest.json").read_text())
    for e in manifest["invoices"]:
        if not e["designed_valid"]:
            continue
        r = etree.parse(str(out / e["file"])).getroot()
        lines = sum(Decimal(x.text) for x in r.xpath("cac:InvoiceLine/cbc:LineExtensionAmount", namespaces=NS))
        lmt = "cac:LegalMonetaryTotal/cbc:"
        tax = _n(r, "cac:TaxTotal/cbc:TaxAmount")
        assert _n(r, lmt + "LineExtensionAmount") == lines
        assert _n(r, lmt + "TaxExclusiveAmount") == lines
        assert _n(r, lmt + "TaxInclusiveAmount") == lines + tax
        assert _n(r, lmt + "PayableAmount") == lines + tax
        subtotal_tax = sum(Decimal(x.text) for x in r.xpath("cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount", namespaces=NS))
        assert subtotal_tax == tax


def test_totals_mutations_break_exactly_their_relation(out):
    manifest = json.loads((out / "manifest.json").read_text())
    by_id = {e["id"]: e for e in manifest["invoices"]}
    for e in by_id.values():
        if e["mutations"] != ["bad_payable"]:
            continue
        r = etree.parse(str(out / e["file"])).getroot()
        incl = _n(r, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount")
        assert _n(r, "cac:LegalMonetaryTotal/cbc:PayableAmount") != incl
