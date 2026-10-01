"""Ask a model for a JSON object, tolerating providers or models without JSON mode."""

from dataclasses import asdict, dataclass

from openai import BadRequestError

from facturaguard.llm.client import LLMClient, Role
from facturaguard.llm.jsonparse import ModelOutputError, parse_json_object


@dataclass
class CallRecord:
    purpose: str
    model: str
    latency_s: float
    prompt_tokens: int | None
    completion_tokens: int | None
    ok: bool
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def ask_json(
    llm: LLMClient,
    role: Role,
    messages: list[dict],
    *,
    purpose: str,
    max_tokens: int,
    calls: list[CallRecord],
) -> dict:
    """One call, with JSON mode if accepted; one corrective retry if the output is not JSON."""
    json_mode = True
    for attempt in range(2):
        try:
            res = llm.chat(role, messages, max_tokens=max_tokens, json_mode=json_mode,
                           temperature=0.1)
        except BadRequestError:
            if not json_mode:
                raise
            json_mode = False  # some models reject response_format; retry without it
            res = llm.chat(role, messages, max_tokens=max_tokens, temperature=0.1)
        record = CallRecord(purpose, res.model, round(res.latency_s, 2), res.prompt_tokens,
                            res.completion_tokens, ok=True)
        calls.append(record)
        try:
            return parse_json_object(res.text)
        except ModelOutputError as e:
            record.ok, record.error = False, str(e)[:200]
            if attempt == 1:
                raise
            messages = messages + [
                {"role": "assistant", "content": res.text[:2000]},
                {"role": "user", "content": "That was not valid JSON. Reply with the JSON "
                                            "object only, no prose and no code fences."},
            ]
    raise ModelOutputError("unreachable")
