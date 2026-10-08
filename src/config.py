from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class LiveKitConfig(BaseSettings):
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_AGENT_NAME: str = "animal-chat-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class AnthropicConfig(BaseSettings):
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str
    ANTHROPIC_MAX_TOKEN: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class SpeechConfig(BaseSettings):
    DEEPGRAM_API_KEY: str
    DEEPGRAM_MODEL: str = "nova-2"
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class ExaConfig(BaseSettings):
    EXA_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class AgentApiConfig(BaseSettings):
    ANIMAL_API_URL: str
    AGENT_SERVICE_TOKEN: str = Field(min_length=32)
    AGENT_API_TIMEOUT_SECONDS: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig()


@lru_cache
def get_livekit_config() -> LiveKitConfig:
    return LiveKitConfig()


@lru_cache
def get_anthropic_config() -> AnthropicConfig:
    return AnthropicConfig()


@lru_cache
def get_speech_config() -> SpeechConfig:
    return SpeechConfig()


@lru_cache
def get_exa_config() -> ExaConfig:
    return ExaConfig()


@lru_cache
def get_agent_api_config() -> AgentApiConfig:
    return AgentApiConfig()
