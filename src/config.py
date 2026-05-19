"""Centralized application configuration.

All runtime defaults should live here. Modules may still accept explicit
arguments, but their default values should be sourced from this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from os import getenv
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数") from exc


def _get_float(name: str, default: float) -> float:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是数字") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_list(name: str, default: list[str]) -> list[str]:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True, slots=True)
class ApiSettings:
    title: str = getenv("RAG_API_TITLE", "RAG Starter API")
    version: str = getenv("RAG_API_VERSION", "0.1.0")
    cors_origins: list[str] = field(
        default_factory=lambda: _get_list(
            "RAG_CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        )
    )


@dataclass(frozen=True, slots=True)
class SplitterSettings:
    default_type: str = getenv("RAG_SPLITTER_TYPE", "recursive")
    default_chunk_size: int = _get_int("RAG_CHUNK_SIZE", 1000)
    default_chunk_overlap: int = _get_int("RAG_CHUNK_OVERLAP", 200)


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    provider: str = getenv("RAG_EMBEDDING_PROVIDER", "dashscope")
    api_key: str = getenv("DASHSCOPE_API_KEY", "")
    base_url: str = getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model: str = getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
    dimension: int = _get_int("DASHSCOPE_EMBEDDING_DIMENSION", _get_int("RAG_EMBEDDING_DIMENSION", 2048))
    batch_size: int = _get_int("DASHSCOPE_EMBEDDING_BATCH_SIZE", 10)
    timeout_seconds: float = _get_float("DASHSCOPE_EMBEDDING_TIMEOUT_SECONDS", 60.0)
    ollama_base_url: str = getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:4b")
    ollama_dimension: int = _get_int("OLLAMA_EMBEDDING_DIMENSION", _get_int("RAG_EMBEDDING_DIMENSION", 2560))
    ollama_batch_size: int = _get_int("OLLAMA_EMBEDDING_BATCH_SIZE", 10)
    ollama_timeout_seconds: float = _get_float("OLLAMA_EMBEDDING_TIMEOUT_SECONDS", 120.0)

    @property
    def active_dimension(self) -> int:
        if self.provider.strip().lower() == "ollama":
            return self.ollama_dimension
        return self.dimension


@dataclass(frozen=True, slots=True)
class VectorStoreSettings:
    persist_directory: str = getenv("RAG_CHROMA_PERSIST_DIRECTORY", "storage/chroma")
    collection_name: str = getenv("RAG_CHROMA_COLLECTION_NAME", "documents")


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str = getenv("RAG_DATABASE_URL", "sqlite:///storage/app.db")


@dataclass(frozen=True, slots=True)
class RagSettings:
    default_top_k: int = _get_int("RAG_TOP_K", 2)
    system_prompt: str = getenv(
        "RAG_SYSTEM_PROMPT",
        "你是一个严谨的知识库问答助手。请优先依据参考段落回答；如果参考段落不足以回答，请明确说明无法从知识库中确认。",
    )


@dataclass(frozen=True, slots=True)
class RerankerSettings:
    provider: str = getenv("RAG_RERANKER_PROVIDER", "bge")
    model: str = getenv("RAG_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    device: str = getenv("RAG_RERANKER_DEVICE", "cpu")
    use_fp16: bool = _get_bool("RAG_RERANKER_USE_FP16", False)
    normalize: bool = _get_bool("RAG_RERANKER_NORMALIZE", True)
    ollama_base_url: str = getenv("OLLAMA_RERANKER_BASE_URL", getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ollama_model: str = getenv("OLLAMA_RERANKER_MODEL", "dengcao/bge-reranker-v2-m3")
    ollama_batch_size: int = _get_int("OLLAMA_RERANKER_BATCH_SIZE", 4)
    ollama_timeout_seconds: float = _get_float("OLLAMA_RERANKER_TIMEOUT_SECONDS", 120.0)
    max_passage_chars: int = _get_int("RAG_RERANKER_MAX_PASSAGE_CHARS", 1500)
    min_candidate_k: int = _get_int("RAG_RETRIEVAL_MIN_CANDIDATE_K", 12)
    candidate_multiplier: int = _get_int("RAG_RETRIEVAL_CANDIDATE_MULTIPLIER", 5)
    max_candidate_k: int = _get_int("RAG_RETRIEVAL_MAX_CANDIDATE_K", 40)
    tool_max_k: int = _get_int("RAG_TOOL_MAX_K", 8)
    tool_max_calls: int = _get_int("RAG_TOOL_MAX_CALLS", 3)


@dataclass(frozen=True, slots=True)
class LlmSettings:
    provider: str = getenv("RAG_LLM_PROVIDER", "deepseek")
    api_key: str = getenv("DEEPSEEK_API_KEY", "")
    base_url: str = getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model: str = getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    temperature: float = _get_float("DEEPSEEK_TEMPERATURE", 0.2)
    max_tokens: int = _get_int("DEEPSEEK_MAX_TOKENS", 1024)
    timeout_seconds: float = _get_float("DEEPSEEK_TIMEOUT_SECONDS", 60.0)


@dataclass(frozen=True, slots=True)
class WeatherSettings:
    default_city: str = getenv("RAG_DEFAULT_CITY", "上海")
    timezone: str = getenv("RAG_TIMEZONE", "Asia/Shanghai")
    geocoding_url: str = getenv("RAG_WEATHER_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search")
    forecast_url: str = getenv("RAG_WEATHER_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
    timeout_seconds: float = _get_float("RAG_WEATHER_TIMEOUT_SECONDS", 10.0)

    def today(self) -> str:
        return datetime.now(ZoneInfo(self.timezone)).date().isoformat()


@dataclass(frozen=True, slots=True)
class GeneratedDocumentSettings:
    directory: str = getenv("RAG_GENERATED_DOCUMENT_DIRECTORY", "storage/generated_documents")


@dataclass(frozen=True, slots=True)
class ChatUploadSettings:
    directory: str = getenv("RAG_CHAT_UPLOAD_DIRECTORY", "storage/chat_uploads")
    max_size_mb: int = _get_int("RAG_CHAT_UPLOAD_MAX_SIZE_MB", 20)
    default_max_chars: int = _get_int("RAG_CHAT_FILE_DEFAULT_MAX_CHARS", 6000)


@dataclass(frozen=True, slots=True)
class AppSettings:
    api: ApiSettings = ApiSettings()
    splitter: SplitterSettings = SplitterSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    database: DatabaseSettings = DatabaseSettings()
    rag: RagSettings = RagSettings()
    reranker: RerankerSettings = RerankerSettings()
    llm: LlmSettings = LlmSettings()
    weather: WeatherSettings = WeatherSettings()
    generated_documents: GeneratedDocumentSettings = GeneratedDocumentSettings()
    chat_uploads: ChatUploadSettings = ChatUploadSettings()


settings = AppSettings()
