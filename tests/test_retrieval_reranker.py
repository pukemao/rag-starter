from __future__ import annotations

import unittest
from unittest.mock import patch

from src.retrieval import RetrievalService
from src.reranker import BGEReranker, DisabledReranker, OllamaReranker
from src.vector_store import SearchResult


class FakeVectorService:
    def __init__(self) -> None:
        self.requests = []

    def search(self, query, *, k=2, filter=None):
        self.requests.append({"query": query, "k": k, "filter": filter})
        return [
            SearchResult(page_content="弱相关内容", metadata={"source": "a.txt"}, score=0.8),
            SearchResult(page_content="强相关内容", metadata={"source": "b.txt"}, score=0.9),
            SearchResult(page_content="中等相关内容", metadata={"source": "c.txt"}, score=0.7),
        ][:k]


class FakeReranker:
    name = "fake-reranker"

    def rerank(self, query, results):
        order = {"强相关内容": 3, "中等相关内容": 2, "弱相关内容": 1}
        return sorted(
            [SearchResult(page_content=item.page_content, metadata=item.metadata, score=item.score, rerank_score=float(order[item.page_content])) for item in results],
            key=lambda item: item.rerank_score or 0,
            reverse=True,
        )


class FakeBGEClient:
    def compute_score(self, pairs, normalize=True):
        return [0.2, 0.9, 0.5]


class FakeHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class RetrievalRerankerTests(unittest.TestCase):
    def test_disabled_reranker_keeps_vector_order(self):
        results = [
            SearchResult(page_content="first", score=0.1),
            SearchResult(page_content="second", score=0.2),
        ]

        reranked = DisabledReranker().rerank("query", results)

        self.assertEqual([item.page_content for item in reranked], ["first", "second"])

    def test_bge_reranker_sorts_by_model_score(self):
        results = [
            SearchResult(page_content="A", score=0.1),
            SearchResult(page_content="B", score=0.2),
            SearchResult(page_content="C", score=0.3),
        ]
        reranker = BGEReranker(model_client=FakeBGEClient())

        reranked = reranker.rerank("query", results)

        self.assertEqual([item.page_content for item in reranked], ["B", "C", "A"])
        self.assertEqual([item.rerank_score for item in reranked], [0.9, 0.5, 0.2])

    def test_ollama_reranker_uses_scores_when_available(self):
        results = [
            SearchResult(page_content="A", score=0.1),
            SearchResult(page_content="B", score=0.2),
            SearchResult(page_content="C", score=0.3),
        ]
        payload = b'{"scores":[0.2,0.9,0.5],"embeddings":[]}'

        with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(payload)):
            reranked = OllamaReranker(model="dengcao/bge-reranker-v2-m3").rerank("query", results)

        self.assertEqual([item.page_content for item in reranked], ["B", "C", "A"])
        self.assertEqual([item.rerank_score for item in reranked], [0.9, 0.5, 0.2])

    def test_ollama_reranker_falls_back_to_cosine_similarity(self):
        results = [
            SearchResult(page_content="A", score=0.1),
            SearchResult(page_content="B", score=0.2),
        ]
        payloads = iter(
            [
                b'{"embeddings":[[0.0,0.1],[0.0,0.2]]}',
                b'{"embeddings":[[1.0,0.0]]}',
                b'{"embeddings":[[0.2,0.9],[0.9,0.1]]}',
            ]
        )

        with patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: FakeHTTPResponse(next(payloads))):
            reranked = OllamaReranker(model="dengcao/bge-reranker-v2-m3").rerank("query", results)

        self.assertEqual([item.page_content for item in reranked], ["B", "A"])
        self.assertGreater(reranked[0].rerank_score or 0, reranked[1].rerank_score or 0)

    def test_retrieval_uses_candidate_k_then_returns_top_k(self):
        vector_service = FakeVectorService()
        retrieval = RetrievalService(vector_service=vector_service, reranker=FakeReranker())

        results = retrieval.retrieve("问题", k=2)

        self.assertEqual(vector_service.requests[0]["k"], 12)
        self.assertEqual([item.page_content for item in results], ["强相关内容", "中等相关内容"])
        self.assertEqual(results[0].rerank_score, 3.0)

    def test_two_stage_retrieval_recalls_more_candidates_then_reranks_top_n(self):
        class WideVectorService:
            def __init__(self):
                self.requests = []

            def search(self, query, *, k=2, filter=None):
                self.requests.append({"query": query, "k": k, "filter": filter})
                return [
                    SearchResult(page_content=f"候选{i}", metadata={"chunk_hash": f"h{i}"}, score=float(i))
                    for i in range(20)
                ][:k]

        class CrossEncoderReranker:
            name = "cross-encoder"

            def __init__(self):
                self.pairs = []

            def rerank(self, query, results):
                self.pairs = [(query, result.page_content) for result in results]
                return sorted(
                    [
                        SearchResult(
                            page_content=result.page_content,
                            metadata=result.metadata,
                            score=result.score,
                            rerank_score=1.0 if result.page_content == "候选11" else 0.1,
                        )
                        for result in results
                    ],
                    key=lambda item: item.rerank_score or 0,
                    reverse=True,
                )

        vector_service = WideVectorService()
        reranker = CrossEncoderReranker()
        retrieval = RetrievalService(vector_service=vector_service, reranker=reranker)

        results = retrieval.retrieve("问题", k=2, candidate_k=20)

        self.assertEqual(vector_service.requests[0]["k"], 20)
        self.assertEqual(len(reranker.pairs), 20)
        self.assertEqual(reranker.pairs[0], ("问题", "候选0"))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].page_content, "候选11")
        self.assertEqual(results[0].rerank_score, 1.0)

    def test_retrieval_deduplicates_candidates_before_reranking(self):
        class DuplicateVectorService:
            def search(self, query, *, k=2, filter=None):
                return [
                    SearchResult(page_content="重复段落", metadata={"chunk_hash": "same"}, score=0.8),
                    SearchResult(page_content="重复段落", metadata={"chunk_hash": "same"}, score=0.2),
                    SearchResult(page_content="唯一段落", metadata={"chunk_hash": "unique"}, score=0.4),
                ]

        class CountingReranker:
            name = "counting-reranker"

            def __init__(self):
                self.seen = []

            def rerank(self, query, results):
                self.seen = results
                return [
                    SearchResult(
                        page_content=result.page_content,
                        metadata=result.metadata,
                        score=result.score,
                        rerank_score=1.0 - index * 0.1,
                    )
                    for index, result in enumerate(results)
                ]

        reranker = CountingReranker()
        retrieval = RetrievalService(vector_service=DuplicateVectorService(), reranker=reranker)

        results = retrieval.retrieve("问题", k=2)

        self.assertEqual(len(reranker.seen), 2)
        self.assertEqual({item.metadata["chunk_hash"] for item in reranker.seen}, {"same", "unique"})
        self.assertEqual([item.metadata["chunk_hash"] for item in results], ["same", "unique"])


if __name__ == "__main__":
    unittest.main()
