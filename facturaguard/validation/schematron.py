"""Run the compiled CIUS-RO Schematron (XSLT 2.0) with Saxon and parse the SVRL report."""

import threading
from functools import lru_cache
from pathlib import Path

from lxml import etree
from saxonche import PySaxonProcessor

from facturaguard.validation.models import Issue

XSLT_PATH = (
    Path(__file__).resolve().parents[2] / "vendor" / "anaf" / "compiled" / "ro16931-ubl-1.0.9.xslt"
)
SVRL = {"svrl": "http://purl.oclc.org/dsdl/schematron"}
_lock = threading.Lock()  # Saxon processor objects are not thread-safe


@lru_cache
def _engine():
    proc = PySaxonProcessor(license=False)
    exe = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(XSLT_PATH))
    return proc, exe


def validate_schematron(xml: bytes) -> list[Issue]:
    with _lock:
        proc, exe = _engine()
        node = proc.parse_xml(xml_text=xml.decode("utf-8"))
        svrl = exe.transform_to_string(xdm_node=node)
    report = etree.fromstring(svrl.encode("utf-8"))
    issues = []
    for el in report.iter("{*}failed-assert", "{*}successful-report"):
        flag = el.get("flag", "fatal")
        issues.append(
            Issue(
                layer="schematron",
                rule_id=el.get("id", "unknown"),
                severity="warning" if flag == "warning" else "fatal",
                message=" ".join("".join(el.xpath("string(svrl:text)", namespaces=SVRL)).split()),
                location=el.get("location", ""),
                test=el.get("test", ""),
            )
        )
    return issues
