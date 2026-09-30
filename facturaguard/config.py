from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.us-central1.nebius.com/v1/"

    model_fast: str = "nvidia/Nemotron-3_5-Lightning"
    model_reasoning: str = "nvidia/Nemotron-3-Ultra-550b-a55b"
    model_balanced: str = "nvidia/nemotron-3-super-120b-a12b"
    model_vision: str = "nvidia/nemotron-3-nano-omni"

    llm_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
