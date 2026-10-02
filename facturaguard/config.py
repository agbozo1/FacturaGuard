from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.us-central1.nebius.com/v1/"

    model_fast: str = "nvidia/Nemotron-3_5-Lightning"
    model_reasoning: str = "nvidia/Nemotron-3-Ultra-550b-a55b"
    model_balanced: str = "nvidia/nemotron-3-super-120b-a12b"
    # Reads scanned invoices (image to text only; Nemotron does the rest). No Nemotron vision model
    # was on our key, so this is MiniCPM-V, verified on Token Factory 2026-10-02. Empty = scans off.
    model_vision: str = "openbmb/MiniCPM-V-4_5"

    llm_timeout_seconds: float = 60.0
    # Optional JSON merged into every request body, e.g. to switch off thinking.
    llm_extra_body: str = ""
    # Lightning is a reasoning model. Verified on Token Factory 2026-09-30: this switches thinking off.
    llm_extra_body_fast: str = '{"chat_template_kwargs": {"enable_thinking": false}}'

    # Tavily web search, restricted to official Romanian sources. Empty = feature off.
    tavily_api_key: str = ""
    tavily_timeout_seconds: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
