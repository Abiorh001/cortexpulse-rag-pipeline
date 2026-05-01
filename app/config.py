from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _flatten_config(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "guardian_query": data.get("news", {}).get("guardian_query"),
        "max_articles": data.get("news", {}).get("max_articles"),
        "sample_articles_path": data.get("news", {}).get("sample_articles_path"),
        "chunk_size": data.get("chunking", {}).get("chunk_size"),
        "chunk_overlap": data.get("chunking", {}).get("chunk_overlap"),
        "retrieval_top_k": data.get("retrieval", {}).get("top_k"),
        "retrieval_score_threshold": data.get("retrieval", {}).get(
            "score_threshold"
        ),
        "citation_snippet_chars": data.get("retrieval", {}).get(
            "citation_snippet_chars"
        ),
        "openai_chat_model": data.get("openai", {}).get("chat_model"),
        "openai_embedding_model": data.get("openai", {}).get("embedding_model"),
        "contextualization_enabled": data.get("openai", {}).get(
            "contextualization_enabled"
        ),
        "openai_answer_temperature": data.get("openai", {}).get(
            "answer_temperature"
        ),
        "openai_contextualize_temperature": data.get("openai", {}).get(
            "contextualize_temperature"
        ),
        "max_article_context_chars": data.get("openai", {}).get(
            "max_article_context_chars"
        ),
        "contextualization_concurrency": data.get("openai", {}).get(
            "contextualization_concurrency"
        ),
        "qdrant_url": data.get("qdrant", {}).get("url"),
        "qdrant_collection": data.get("qdrant", {}).get("collection"),
        "request_timeout_seconds": data.get("resilience", {}).get(
            "request_timeout_seconds"
        ),
        "retry_attempts": data.get("resilience", {}).get("retry_attempts"),
        "retry_initial_backoff_seconds": data.get("resilience", {}).get(
            "retry_initial_backoff_seconds"
        ),
        "retry_backoff_multiplier": data.get("resilience", {}).get(
            "retry_backoff_multiplier"
        ),
        "circuit_breaker_failure_threshold": data.get("resilience", {}).get(
            "circuit_breaker_failure_threshold"
        ),
        "circuit_breaker_reset_seconds": data.get("resilience", {}).get(
            "circuit_breaker_reset_seconds"
        ),
    }


def _load_yaml_defaults() -> dict[str, Any]:
    config_path = Path(os.getenv("CORTEXPULSE_CONFIG", "config.yaml"))
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return {key: value for key, value in _flatten_config(data).items() if value is not None}


YAML_DEFAULTS = _load_yaml_defaults()


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    guardian_api_key: str = Field(default="", alias="GUARDIAN_API_KEY")
    openai_chat_model: str = Field(
        default=YAML_DEFAULTS.get("openai_chat_model", "gpt-4o-mini"),
        alias="OPENAI_CHAT_MODEL",
    )
    openai_embedding_model: str = Field(
        default=YAML_DEFAULTS.get("openai_embedding_model", "text-embedding-3-small"),
        alias="OPENAI_EMBEDDING_MODEL",
    )
    contextualization_enabled: bool = Field(
        default=YAML_DEFAULTS.get("contextualization_enabled", False),
        alias="CONTEXTUALIZATION_ENABLED",
    )
    openai_answer_temperature: float = Field(
        default=YAML_DEFAULTS.get("openai_answer_temperature", 0.2),
        alias="OPENAI_ANSWER_TEMPERATURE",
    )
    openai_contextualize_temperature: float = Field(
        default=YAML_DEFAULTS.get("openai_contextualize_temperature", 0),
        alias="OPENAI_CONTEXTUALIZE_TEMPERATURE",
    )
    max_article_context_chars: int = Field(
        default=YAML_DEFAULTS.get("max_article_context_chars", 6000),
        alias="MAX_ARTICLE_CONTEXT_CHARS",
    )
    contextualization_concurrency: int = Field(
        default=YAML_DEFAULTS.get("contextualization_concurrency", 2),
        alias="CONTEXTUALIZATION_CONCURRENCY",
    )
    qdrant_url: str = Field(
        default=YAML_DEFAULTS.get("qdrant_url", "http://localhost:6333"),
        alias="QDRANT_URL",
    )
    qdrant_collection: str = Field(
        default=YAML_DEFAULTS.get("qdrant_collection", "cortexpulse_news"),
        alias="QDRANT_COLLECTION",
    )
    guardian_query: str = Field(
        default=YAML_DEFAULTS.get("guardian_query", "artificial intelligence"),
        alias="GUARDIAN_QUERY",
    )
    max_articles: int = Field(default=YAML_DEFAULTS.get("max_articles", 1), alias="MAX_ARTICLES")
    sample_articles_path: str = Field(
        default=YAML_DEFAULTS.get("sample_articles_path", "data/sample_articles.json"),
        alias="SAMPLE_ARTICLES_PATH",
    )
    chunk_size: int = Field(default=YAML_DEFAULTS.get("chunk_size", 400), alias="CHUNK_SIZE")
    chunk_overlap: int = Field(
        default=YAML_DEFAULTS.get("chunk_overlap", 200), alias="CHUNK_OVERLAP"
    )
    retrieval_top_k: int = Field(
        default=YAML_DEFAULTS.get("retrieval_top_k", 4), alias="RETRIEVAL_TOP_K"
    )
    retrieval_score_threshold: float = Field(
        default=YAML_DEFAULTS.get("retrieval_score_threshold", 0.3),
        alias="RETRIEVAL_SCORE_THRESHOLD",
    )
    citation_snippet_chars: int = Field(
        default=YAML_DEFAULTS.get("citation_snippet_chars", 260),
        alias="CITATION_SNIPPET_CHARS",
    )
    request_timeout_seconds: float = Field(
        default=YAML_DEFAULTS.get("request_timeout_seconds", 20),
        alias="REQUEST_TIMEOUT_SECONDS",
    )
    retry_attempts: int = Field(
        default=YAML_DEFAULTS.get("retry_attempts", 3), alias="RETRY_ATTEMPTS"
    )
    retry_initial_backoff_seconds: float = Field(
        default=YAML_DEFAULTS.get("retry_initial_backoff_seconds", 0.75),
        alias="RETRY_INITIAL_BACKOFF_SECONDS",
    )
    retry_backoff_multiplier: float = Field(
        default=YAML_DEFAULTS.get("retry_backoff_multiplier", 2),
        alias="RETRY_BACKOFF_MULTIPLIER",
    )
    circuit_breaker_failure_threshold: int = Field(
        default=YAML_DEFAULTS.get("circuit_breaker_failure_threshold", 3),
        alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD",
    )
    circuit_breaker_reset_seconds: float = Field(
        default=YAML_DEFAULTS.get("circuit_breaker_reset_seconds", 30),
        alias="CIRCUIT_BREAKER_RESET_SECONDS",
    )

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be greater than zero")
        if self.chunk_overlap < 0:
            raise ValueError("CHUNK_OVERLAP cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.retry_attempts < 1:
            raise ValueError("RETRY_ATTEMPTS must be at least 1")
        if self.contextualization_concurrency < 1:
            raise ValueError("CONTEXTUALIZATION_CONCURRENCY must be at least 1")
        if not 0 <= self.retrieval_score_threshold <= 1:
            raise ValueError("RETRIEVAL_SCORE_THRESHOLD must be between 0 and 1")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
