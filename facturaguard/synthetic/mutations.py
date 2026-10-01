"""Planted errors. Each mutation declares the rules that MUST fire (expected_rules).

Validators may report extra cascading findings; tests check recall on expected_rules.
Rule IDs are EN 16931 / CIUS-RO IDs, confirmed against ro16931-ubl-1.0.9 and ANAF's offline
validator. FG-* IDs are ANAF identifier checks that run outside the Schematron (see
facturaguard/validation/identifiers.py). XSD and parse mutations have no rule ID and are
identified by layer.
"""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass

from facturaguard.synthetic.identifiers import corrupt_cui
from facturaguard.synthetic.invoice import eu_party, shift


@dataclass(frozen=True)
class Mutation:
    name: str
    layer: str  # parse | xsd | schematron | anaf_identifier
    rules: tuple[str, ...]
    description: str
    group: str
    model_fn: Callable[[dict], None] | None = None
    xml_fn: Callable[[str], str] | None = None
    combinable: bool = True
    needs_rule_mapping: bool = False


def _set(path: tuple[str, ...], value):
    def fn(m: dict) -> None:
        target = m
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return fn


def _strip_vat_prefix(m: dict) -> None:
    m["seller"]["vat_id"] = m["seller"]["vat_id"].removeprefix("RO")


def _bad_cif(m: dict) -> None:
    m["seller"]["vat_id"] = "RO" + corrupt_cui(m["seller"]["vat_id"].removeprefix("RO"))


def _foreign_buyer(m: dict) -> None:
    m["buyer"] = eu_party(random.Random(m["number"] or "x"))


def _xml_wrong_order(xml: str) -> str:
    match = re.search(r"\n\s*<cbc:ID>[^<]*</cbc:ID>", xml)
    moved = match.group(0)
    xml = xml.replace(moved, "", 1)
    return xml.replace("</cbc:IssueDate>", "</cbc:IssueDate>" + moved, 1)


def _xml_unknown_element(xml: str) -> str:
    return re.sub(r"(<cbc:ID>[^<]*</cbc:ID>)", r"\1<cbc:Foo>x</cbc:Foo>", xml, count=1)


def _xml_truncate(xml: str) -> str:
    return xml[: int(len(xml) * 0.6)]


def _totals(name, rule, desc, **deltas) -> Mutation:
    return Mutation(name, "schematron", (rule,), desc, "totals", lambda m: shift(m, **deltas))


def _missing(name, rule, desc, setter, group=None) -> Mutation:
    return Mutation(name, "schematron", (rule,), desc, group or name, setter)


MUTATIONS: list[Mutation] = [
    _totals("bad_payable", "BR-CO-16", "Payable amount does not match tax-inclusive total.",
            payable=5),
    _totals("bad_tax_inclusive", "BR-CO-15", "Tax-inclusive total is not tax-exclusive plus VAT.",
            tax_incl=7, payable=7),
    _totals("bad_tax_exclusive", "BR-CO-13", "Tax-exclusive total does not match line sum.",
            tax_excl=3, tax_incl=3, payable=3),
    _totals("bad_line_sum", "BR-CO-10", "Sum of lines in totals differs from the actual lines.",
            line_sum=11, tax_excl=11, tax_incl=11, payable=11),
    _totals("bad_tax_total", "BR-CO-14", "Invoice VAT total differs from sum of VAT subtotals.",
            tax_total=13, tax_incl=13, payable=13),
    _totals("bad_vat_amount", "BR-CO-17", "VAT subtotal amount is not taxable amount x rate.",
            subtotal_tax=1, tax_total=1, tax_incl=1, payable=1),
    Mutation("vat_no_country_prefix", "schematron", ("BR-CO-09",),
             "Seller VAT id has no ISO country prefix.", "vat_prefix", _strip_vat_prefix),
    Mutation("wrong_country_seller", "schematron", ("BR-CL-14",),
             "Seller country is 'ROU' instead of ISO alpha-2 'RO'.", "seller_country",
             _set(("seller", "country"), "ROU")),
    Mutation("wrong_country_buyer", "schematron", ("BR-CL-14",),
             "Buyer country is 'GER' instead of ISO alpha-2.", "buyer_country",
             _set(("buyer", "country"), "GER")),
    Mutation("bad_currency_code", "schematron", ("BR-CL-03", "BR-CL-04"),
             "Document currency is 'LEI' instead of ISO 4217 'RON'.", "currency",
             _set(("currency",), "LEI")),
    _missing("missing_customization_id", "BR-01", "Missing CustomizationID.",
             _set(("customization",), None)),
    _missing("missing_invoice_number", "BR-02", "Missing invoice number.",
             _set(("number",), None)),
    _missing("missing_issue_date", "BR-03", "Missing issue date.", _set(("issue_date",), None)),
    _missing("missing_type_code", "BR-04", "Missing invoice type code.",
             _set(("type_code",), None)),
    _missing("missing_currency", "BR-05", "Missing document currency code.",
             _set(("currency",), None), group="currency"),
    _missing("missing_seller_name", "BR-06", "Missing seller legal name.",
             _set(("seller", "legal_name"), None)),
    _missing("missing_buyer_name", "BR-07", "Missing buyer legal name.",
             _set(("buyer", "legal_name"), None)),
    _missing("missing_seller_country", "BR-09", "Missing seller country code.",
             _set(("seller", "country"), None), group="seller_country"),
    _missing("missing_buyer_country", "BR-11", "Missing buyer country code.",
             _set(("buyer", "country"), None), group="buyer_country"),
    Mutation("no_invoice_lines", "schematron", ("BR-16",), "Invoice has no lines.", "lines",
             _set(("lines",), []), combinable=False),
    Mutation("bad_cif_checksum", "anaf_identifier", ("FG-CUI-SELLER",),
             "Seller CIF fails the CUI control-digit checksum (checked outside Schematron).",
             "cif", _bad_cif),
    Mutation("foreign_buyer_no_ro_id", "anaf_identifier", ("FG-BUYER-ID",),
             "EU buyer identified only by its foreign VAT id; ANAF's validator finds no buyer CUI.",
             "buyer_id", _foreign_buyer, combinable=False),
    Mutation("missing_ro_subdivision", "schematron", ("BR-RO-110",),
             "Romanian seller address lacks the RO-XX county code (CIUS-RO rule).",
             "subdivision", _set(("seller", "subdivision"), None)),
    Mutation("bad_ro_subdivision", "schematron", ("BR-RO-110",),
             "Romanian seller county is free text, not an RO-XX code (CIUS-RO rule).",
             "subdivision", _set(("seller", "subdivision"), "Cluj")),
    Mutation("xsd_wrong_element_order", "xsd", (), "cbc:ID placed after cbc:IssueDate.",
             "xml", xml_fn=_xml_wrong_order, combinable=False),
    Mutation("xsd_unknown_element", "xsd", (), "Unknown element cbc:Foo inserted.", "xml",
             xml_fn=_xml_unknown_element, combinable=False),
    Mutation("xsd_bad_date", "xsd", (), "Issue date is '31/02/2026', not an xs:date.",
             "issue_date", _set(("issue_date",), "31/02/2026"), combinable=False),
    Mutation("malformed_xml", "parse", (), "File truncated, not well-formed XML.", "xml",
             xml_fn=_xml_truncate, combinable=False),
]
BY_NAME = {m.name: m for m in MUTATIONS}
