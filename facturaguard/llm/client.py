"""The only module that talks to Nebius Token Factory.

Callers ask for a model role ("fast", "reasoning", "balanced", "vision"),
never a model ID. Roles map to IDs in config, so models swap via env vars.
"""

import json
import re
import time
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from facturaguard.config import Settings, get_settings

Role = Literal["fast", "reasoning", "balanced", "vision"]


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class LLMNotConfigured(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    reasoning: str | None
    latency_s: float
    prompt_tokens: int | None
    completion_tokens: int | None


class LLMClient:
    def __init__(self, settings: Settings | None = None, sdk: OpenAI | None = None):
        self.settings = settings or get_settings()
        if sdk is None:
            if not self.settings.nebius_api_key:
                raise LLMNotConfigured("NEBIUS_API_KEY is not set")
            sdk = OpenAI(
                base_url=self.settings.nebius_base_url,
                api_key=self.settings.nebius_api_key,
                timeout=self.settings.llm_timeout_seconds,
            )
        self._sdk = sdk

    def model_for(self, role: Role) -> str:
        return getattr(self.settings, f"model_{role}")

    def list_models(self) -> list[str]:
        return sorted(m.id for m in self._sdk.models.list())

    def chat(
        self,
        role: Role,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
        extra_body: dict | None = None,
    ) -> LLMResult:
        model = self.model_for(role)
        kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        body = json.loads(self.settings.llm_extra_body) if self.settings.llm_extra_body else {}
        body.update(extra_body or {})
        if body:
            kwargs["extra_body"] = body
        start = time.perf_counter()
        resp = self._sdk.chat.completions.create(**kwargs)
        latency = time.perf_counter() - start
        usage = resp.usage
        msg = resp.choices[0].message
        content = msg.content or ""
        # Reasoning models may return thinking separately or inline in <think> tags.
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
        if "<think>" in content:
            reasoning = reasoning or "".join(_THINK_RE.findall(content))
            content = _THINK_RE.sub("", content)
        return LLMResult(
            text=content.strip(),
            reasoning=reasoning,
            model=model,
            latency_s=latency,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )
