import uuid
from pathlib import Path
from typing import Any, Tuple, Type

import httpx
from pydantic import BaseModel, Field, SecretStr, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class MidjourneyConfig(BaseModel):
    user_token: str
    bot_token: str
    guild_id: str
    channel_id: str
    user_agent: str | None = None
    prompt_prefix: str = "<&"
    prompt_suffix: str = ">"
    app_name: str = "midjourney_simple_api"
    rate_limit: int | float = 1 / 4
    interaction_url: str = "https://discord.com/api/v9/interactions"

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)


class RedisConfig(BaseModel):
    host: str
    port: int
    db: int | None = 0
    password: SecretStr | None = ""


class AliyunOssConfig(BaseModel):
    endpoint: str
    access_key_id: str
    access_key_secret: str
    bucket_name: str
    domain: str
    path_prefix: str = "midjourney_simple_api"


class LLMConfig(BaseModel):
    base_url: str
    api_key: str
    model: str | None = None
    models: list[dict] | list[str] = []


class LLMProvider(BaseModel):
    dashscope: LLMConfig | None = None
    ark: LLMConfig | None = None


class JimengConfig(BaseModel):
    base_url: str
    access_key: str
    secret_key: str


class SolutionConfig(BaseModel):
    jimeng: JimengConfig | None = None
    kontext: Any | None = None


class Settings(BaseSettings):
    app_name: str = "ai-tools"
    httpx_timeout: int = 60
    wait_max_seconds: int = 60 * 2
    midjourney: MidjourneyConfig = None
    project_dir: Path = Path(__file__).parent.parent
    temp_dir: Path = project_dir.joinpath("temp")
    oss: AliyunOssConfig = None
    proxy_url: str | None = "http://127.0.0.1:7890"
    redis: RedisConfig | None = None
    redis_expire_time: int = 60 * 60 * 24 * 30
    llms: LLMProvider | None = Field(None, title="LLM提供商配置")
    solutions: SolutionConfig | None = Field(None, title="解决方案配置")
    apps: Any | None = Field(None, title="多应用配置")
    tools: Any | None = Field(None, title="私有化部署工具")
    infras: Any | None = Field(None, title="基础设施配置")
    # ark: ArkConfig = None

    @computed_field
    @property
    def redis_dsn(self) -> str:
        return (
            f"redis://:{self.redis.password.get_secret_value() or ''}@{self.redis.host}:{self.redis.port}/"
            f"{self.redis.db}?health_check_interval=2"
        )

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=[".env"],
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        toml_file=[
            "config.toml",
            "config.dev.toml",
            "config.staging.toml",
            "config.prod.toml",
            "config.local.toml",
            "config.dev.local.toml",
            "config.staging.local.toml",
            "config.prod.local.toml",
        ],
        # yaml_file=[
        #     "config.yml",
        #     "config.dev.yml",
        #     "config.staging.yml",
        #     "config.prod.yml",
        #     "config.local.yml",
        #     "config.dev.local.yml",
        #     "config.staging.local.yml",
        #     "config.prod.local.yml",
        # ],
        # yaml_file_encoding="utf-8",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # The order of the returned callables decides the priority of inputs; first item is the highest priority.
        # 第一个优先级最高
        return (
            env_settings,
            dotenv_settings,
            # YamlConfigSettingsSource(settings_cls),
            TomlConfigSettingsSource(settings_cls),
        )

    @computed_field
    @property
    def http_client(self) -> httpx.Client:
        return httpx.Client(proxy=self.proxy_url or "http://127.0.0.1:7890")

    @computed_field
    @property
    def http_client_async(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(proxy=self.proxy_url or "http://127.0.0.1:7890")


settings = Settings()

if __name__ == "__main__":
    print(settings.midjourney)
    print(settings.midjourney.bot_token)
    print(settings.redis_dsn)
    print(project_dir := settings.project_dir)
