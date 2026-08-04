"""Retrievers for the RAG knowledge base.

Two complementary retrievers:

1. ``VectorRetriever`` — embeds the query and searches the VectorStore.
   Works with any embedding backend (OpenAI or offline hash).
2. ``BM25Retriever`` — a self-contained Okapi-BM25 keyword ranker with no
   external dependencies. Scores on exact token overlap, which complements
   the embedding retrieval (especially for codes like ``P0420`` and proper
   nouns that hash-embeddings handle poorly).

The :class:`HybridRetriever` blends both: it runs vector search, then
boosts any chunk that also matches on BM25, returning a single merged
ranking. This gives the best of semantic + lexical matching.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Sequence

from carsoul_agent.knowledge.base import Chunk, SearchResult
from carsoul_agent.knowledge.embeddings import EmbeddingProvider, HashEmbedding
from carsoul_agent.knowledge.store import VectorStore

logger = logging.getLogger(__name__)

# Regex for splitting tokens — works for Chinese (char-level) and Latin.
_CJK_RANGE = r"\u4e00-\u9fff"


def tokenize(text: str) -> list[str]:
    """Tokenise for BM25: CJK chars + Latin/number words."""
    text = text.lower()
    tokens: list[str] = []
    for word in re.findall(r"[a-z0-9]+", text):
        tokens.append(word)
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            tokens.append(ch)
    return tokens


# ---------------------------------------------------------------------------
class BM25Retriever:
    """Okapi-BM25 over an in-memory corpus (zero dependencies)."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._chunks: list[Chunk] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_freq: Counter[str] = Counter()
        self._avg_len: float = 0.0
        self._n: int = 0

    def index(self, chunks: Sequence[Chunk]) -> None:
        self._chunks = list(chunks)
        self._doc_tokens = [tokenize(c.text) for c in self._chunks]
        self._doc_freq = Counter()
        for toks in self._doc_tokens:
            for t in set(toks):
                self._doc_freq[t] += 1
        self._n = len(self._chunks)
        self._avg_len = (
            sum(len(t) for t in self._doc_tokens) / self._n if self._n else 0.0
        )

    @property
    def ready(self) -> bool:
        return self._n > 0

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if not self._n:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scores: list[float] = [0.0] * self._n
        for qt in q_tokens:
            df = self._doc_freq.get(qt, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
            for i, toks in enumerate(self._doc_tokens):
                tf = toks.count(qt)
                if tf == 0:
                    continue
                dl = len(toks)
                denom = tf + self._k1 * (1 - self._b + self._b * dl / (self._avg_len or 1))
                scores[i] += idf * (tf * (self._k1 + 1)) / denom
        ranked = sorted(
            zip(self._chunks, scores), key=lambda x: x[1], reverse=True
        )
        return [(c, s) for c, s in ranked[:top_k] if s > 0]


# ---------------------------------------------------------------------------
class VectorRetriever:
    """Embedding-based retrieval through the configured VectorStore."""

    def __init__(self, store: VectorStore, embedder: EmbeddingProvider) -> None:
        self._store = store
        self._embedder = embedder

    @property
    def ready(self) -> bool:
        return self._store.ready

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if not self._store.ready:
            return []
        q_vec = self._embedder.embed(query)
        return self._store.search(q_vec, top_k=top_k)


# ---------------------------------------------------------------------------
class HybridRetriever:
    """Blend vector + BM25 for robust retrieval in any environment.

    Vector search catches semantic matches; BM25 catches exact keywords
    and codes. Results are normalised to [0, 1] and summed with weights.
    """

    def __init__(
        self,
        store: VectorStore,
        embedder: EmbeddingProvider,
        bm25: BM25Retriever | None = None,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> None:
        self._vector = VectorRetriever(store, embedder)
        self._bm25 = bm25 or BM25Retriever()
        self._vw = vector_weight
        self._bw = bm25_weight

    def index(self, chunks: Sequence[Chunk]) -> None:
        self._bm25.index(chunks)

    @property
    def ready(self) -> bool:
        return self._vector.ready or self._bm25.ready

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        vec_results = self._vector.search(query, top_k=top_k * 2)
        bm25_results = (
            self._bm25.search(query, top_k=top_k * 2) if self._bm25.ready else []
        )
        return self._blend(query, vec_results, bm25_results, top_k)

    # -- internals ------------------------------------------------------
    def _blend(
        self,
        query: str,
        vec: list[tuple[Chunk, float]],
        bm25: list[tuple[Chunk, float]],
        top_k: int,
    ) -> list[SearchResult]:
        # Normalise scores to [0, 1].
        vec_scores = {c.chunk_id: s for c, s in vec}
        bm25_scores = {c.chunk_id: s for c, s in bm25}
        if vec_scores:
            vmax = max(vec_scores.values())
            if vmax > 0:
                vec_scores = {k: v / vmax for k, v in vec_scores.items()}
        if bm25_scores:
            bmax = max(bm25_scores.values())
            if bmax > 0:
                bm25_scores = {k: v / bmax for k, v in bm25_scores.items()}

        all_ids = set(vec_scores) | set(bm25_scores)
        chunk_map: dict[str, Chunk] = {}
        backend_map: dict[str, str] = {}
        for c, _ in vec:
            chunk_map[c.chunk_id] = c
            backend_map[c.chunk_id] = "vector"
        for c, _ in bm25:
            if c.chunk_id not in chunk_map:
                chunk_map[c.chunk_id] = c
            backend_map[c.chunk_id] = (
                "hybrid" if c.chunk_id in vec_scores else "bm25"
            )

        scored: list[tuple[str, float, str]] = []
        for cid in all_ids:
            v = vec_scores.get(cid, 0.0) * self._vw
            b = bm25_scores.get(cid, 0.0) * self._bw
            scored.append((cid, v + b, backend_map[cid]))

        scored.sort(key=lambda x: x[1], reverse=True)
        results: list[SearchResult] = []
        for cid, score, backend in scored[:top_k]:
            chunk = chunk_map.get(cid)
            if chunk is None:
                continue
            results.append(
                SearchResult(chunk=chunk, score=round(score, 4), backend=backend)
            )
        return results
