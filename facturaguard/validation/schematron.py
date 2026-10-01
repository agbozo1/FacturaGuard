"""Run the compiled CIUS-RO Schematron (XSLT 2.0) with Saxon and parse the SVRL report.

saxonche is a GraalVM native library whose objects are bound to the thread that created them.
Web servers call us from many worker threads, so all Saxon work runs on one dedicated thread
(with a large stack for deep XSLT recursion) and callers wait for its result.
"""

import queue
import threading
from concurrent.futures import Future
from pathlib import Path

from lxml import etree

from facturaguard.validation.models import Issue

XSLT_PATH = (
    Path(__file__).resolve().parents[2] / "vendor" / "anaf" / "compiled" / "ro16931-ubl-1.0.9.xslt"
)
SVRL = {"svrl": "http://purl.oclc.org/dsdl/schematron"}
STACK_BYTES = 64 * 1024 * 1024


class _SaxonWorker:
    def __init__(self):
        self._jobs: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()

    def _run(self) -> None:
        from saxonche import PySaxonProcessor  # import on the worker thread

        proc = PySaxonProcessor(license=False)
        exe = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(XSLT_PATH))
        while True:
            xml, fut = self._jobs.get()
            if fut.set_running_or_notify_cancel():
                try:
                    node = proc.parse_xml(xml_text=xml.decode("utf-8"))
                    fut.set_result(exe.transform_to_string(xdm_node=node))
                except Exception as e:  # noqa: BLE001  hand any Saxon error to the caller
                    fut.set_exception(e)

    def _ensure_started(self) -> None:
        with self._start_lock:
            if self._thread is None:
                old = threading.stack_size()
                threading.stack_size(STACK_BYTES)
                try:
                    self._thread = threading.Thread(target=self._run, name="saxon", daemon=True)
                    self._thread.start()
                finally:
                    threading.stack_size(old)

    def transform(self, xml: bytes, timeout: float = 60.0) -> str:
        self._ensure_started()
        fut: Future = Future()
        self._jobs.put((xml, fut))
        return fut.result(timeout=timeout)


_worker = _SaxonWorker()


def validate_schematron(xml: bytes) -> list[Issue]:
    svrl = _worker.transform(xml)
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
