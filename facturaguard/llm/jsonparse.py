"""Tolerant JSON extraction from model output (code fences, leading prose, trailing text)."""

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class ModelOutputError(ValueError):
    pass


def parse_json_object(text: str) -> dict:
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    for cand in candidates:
        start = cand.find("{")
        while start != -1:
            try:
                obj, _ = json.JSONDecoder().raw_decode(cand[start:])
            except json.JSONDecodeError:
                start = cand.find("{", start + 1)
                continue
            if isinstance(obj, dict):
                return obj
            start = cand.find("{", start + 1)
    raise ModelOutputError(f"no JSON object in model output: {text[:200]!r}")
