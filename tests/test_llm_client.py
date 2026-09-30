from types import SimpleNamespace

import pytest

from facturaguard.config import Settings
from facturaguard.llm.client import LLMClient, LLMNotConfigured


class FakeSDK:
    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="b"), SimpleNamespace(id="a")])

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=1),
        )


def test_role_maps_to_configured_model():
    s = Settings(nebius_api_key="x", model_fast="my/fast")
    c = LLMClient(s, sdk=FakeSDK())
    assert c.model_for("fast") == "my/fast"


def test_chat_passes_model_and_json_mode():
    sdk = FakeSDK()
    c = LLMClient(Settings(nebius_api_key="x"), sdk=sdk)
    r = c.chat("reasoning", [{"role": "user", "content": "hi"}], json_mode=True)
    assert r.text == "ok" and r.completion_tokens == 1
    assert sdk.calls[0]["model"] == c.model_for("reasoning")
    assert sdk.calls[0]["response_format"] == {"type": "json_object"}


def test_think_tags_stripped_and_extra_body_forwarded():
    sdk = FakeSDK()
    sdk.chat.completions.create = lambda **kw: (
        sdk.calls.append(kw)
        or SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="<think>hmm</think>answer"))],
            usage=None,
        )
    )
    c = LLMClient(Settings(nebius_api_key="x"), sdk=sdk)
    r = c.chat("fast", [], extra_body={"a": 1})
    assert r.text == "answer" and r.reasoning == "<think>hmm</think>"
    assert sdk.calls[0]["extra_body"] == {"a": 1}


def test_list_models_sorted():
    assert LLMClient(Settings(nebius_api_key="x"), sdk=FakeSDK()).list_models() == ["a", "b"]


def test_missing_key_raises():
    with pytest.raises(LLMNotConfigured):
        LLMClient(Settings(nebius_api_key=""))
