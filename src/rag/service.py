"""RAG retrieval and answer generation service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.config import settings
from src.llm import DeepSeekClient, LLMResponse
from src.vector_store import SearchResult, VectorStoreService


class ChatClient(Protocol):
    """Protocol for LLM clients used by the RAG service."""

    model: str

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Return an answer for the provided prompt."""


@dataclass(frozen=True, slots=True)
class RagReference:
    """One retrieved knowledge-base chunk used as answer context."""

    index: int
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


@dataclass(frozen=True, slots=True)
class RagAnswer:
    """Full RAG response including prompt and retrieved references."""

    answer: str
    question: str
    prompt: str
    references: list[RagReference]
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class RagService:
    """Run retrieval, prompt assembly, and LLM answer generation."""

    def __init__(
        self,
        *,
        vector_service: VectorStoreService | None = None,
        llm_client: ChatClient | None = None,
        system_prompt: str = settings.rag.system_prompt,
    ) -> None:
        self.vector_service = vector_service or VectorStoreService()
        self.llm_client = llm_client or DeepSeekClient()
        self.system_prompt = system_prompt

    def answer(
        self,
        question: str,
        *,
        k: int = settings.rag.default_top_k,
        filter: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> RagAnswer:
        """Answer a question using top-k local vector-store matches as context."""

        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question 不能为空")
        if k <= 0:
            raise ValueError("k 必须大于 0")

        search_results = self.vector_service.search(normalized_question, k=k, filter=filter)
        references = self._to_references(search_results)
        prompt = self.build_prompt(normalized_question, references)
        llm_response = self.llm_client.chat(
            prompt,
            system_prompt=system_prompt or self.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return RagAnswer(
            answer=llm_response.content,
            question=normalized_question,
            prompt=prompt,
            references=references,
            model=llm_response.model,
            usage=llm_response.usage,
        )

    @staticmethod
    def build_prompt(question: str, references: list[RagReference]) -> str:
        """Build the final user prompt from the original question and references."""

        if references:
            context = "\n\n".join(RagService._format_reference(reference) for reference in references)
        else:
            context = "未检索到与问题相关的知识库段落。"

        return (
            "请基于以下参考段落回答用户问题。\n"
            "如果参考段落无法支持答案，请明确说明无法从知识库中确认，不要编造事实。\n\n"
            f"用户问题：\n{question}\n\n"
            f"参考段落：\n{context}\n\n"
            "回答要求：\n"
            "1. 优先使用参考段落中的信息。\n"
            "2. 回答应简洁、准确。\n"
            "3. 如引用具体信息，请尽量说明对应的参考段落编号。"
        )

    @staticmethod
    def _to_references(search_results: list[SearchResult]) -> list[RagReference]:
        return [
            RagReference(
                index=index,
                page_content=result.page_content,
                metadata=result.metadata,
                score=result.score,
            )
            for index, result in enumerate(search_results, start=1)
        ]

    @staticmethod
    def _format_reference(reference: RagReference) -> str:
        source = reference.metadata.get("source") or reference.metadata.get("source_id") or "unknown"
        score = "" if reference.score is None else f"，score={reference.score}"
        return f"[{reference.index}] source={source}{score}\n{reference.page_content}"
