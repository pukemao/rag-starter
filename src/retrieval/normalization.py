"""Candidate normalization for two-stage retrieval."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from src.vector_store import SearchResult

_WHITESPACE_PATTERN = re.compile(r"\s+")


def dedupe_candidates(results: Iterable[SearchResult]) -> list[SearchResult]:
    """Deduplicate vector recall candidates before cross-encoder reranking."""

    unique: dict[str, SearchResult] = {}
    for result in results:
        key = _candidate_key(result)
        current = unique.get(key)
        if current is None or _is_better_vector_candidate(result, current):
            unique[key] = result
    return list(unique.values())


def _candidate_key(result: SearchResult) -> str:
    metadata = result.metadata
    chunk_hash = str(metadata.get("chunk_hash") or "").strip()
    if chunk_hash:
        return f"chunk:{chunk_hash}"

    source_id = str(metadata.get("source_id") or "").strip()
    source = str(metadata.get("source") or metadata.get("filename") or "").strip()
    chunk_index = metadata.get("chunk_index")
    if chunk_index is not None and (source_id or source):
        return f"source-chunk:{source_id or source}:{chunk_index}"

    normalized = _WHITESPACE_PATTERN.sub(" ", result.page_content).strip()
    return f"content:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def _is_better_vector_candidate(candidate: SearchResult, current: SearchResult) -> bool:
    """Prefer the candidate with the smaller vector distance before reranking."""

    if candidate.score is None and current.score is None:
        return len(candidate.page_content) > len(current.page_content)
    if candidate.score is None:
        return False
    if current.score is None:
        return True
    return candidate.score < current.score
