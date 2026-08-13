"""Vector stores for the RAG knowledge base.

Two backends behind one interface:

1. ``ChromaVectorStore`` — persistent on-disk store via ChromaDB. Used
   automatically when ``chromadb`` is importable. Survives restarts.
2. ``InMemoryVectorStore`` — pure-Python cosine-similarity store. Used as
   a fallback when ChromaDB is not installed. Rebuilt from docs on startup.

Both are created through :func:`default_vector_store` which probes for
ChromaDB and degrades gracefully.
"""
from __future__ import annotations

import logging
import math
import os
from abc import ABC, abstractmethod

from carsoul_agent.knowledge.base import Chunk

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Persistence + similarity-search contract for chunk embeddings."""

    name: str = "base"

    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None:
        """Insert or update chunks (embedding already attached)."""

    @abstractmethod
    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Chunk, float]]:
        """Return ``(chunk, score)`` pairs ranked by similarity."""

    @abstractmethod
    def count(self) -> int:
        """Number of stored chunks."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all chunks."""

    @abstractmethod
    def get_embedder_tag(self) -> str | None:
        """Return the embedder id the stored vectors were built with, or None."""

    @abstractmethod
    def set_embedder_tag(self, tag: str) -> None:
        """Record the embedder id used to build the stored vectors."""

    @property
    def ready(self) -> bool:
        """Whether the store is usable (has data loaded)."""
        return self.count() > 0


# ---------------------------------------------------------------------------
class ChromaVectorStore(VectorStore):
    """Persistent vector store backed by ChromaDB."""

    name = "chroma"

    def __init__(self, persist_path: str, collection_name: str) -> None:
        self._persist_path = persist_path
        self._collection_name = collection_name
        self._client = None
        self._collection = None
        try:
            import chromadb  # type: ignore

            os.makedirs(persist_path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_path)
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB store ready at %s (collection=%s, existing=%d)",
                persist_path,
                collection_name,
                self._collection.count(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChromaDB init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._collection is not None

    def upsert(self, chunks: list[Chunk]) -> None:
        if not self._collection:
            raise RuntimeError("ChromaDB collection not available")
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[self._meta(c) for c in chunks],
        )

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Chunk, float]]:
        if not self._collection or self._collection.count() == 0:
            return []
        n = min(top_k, self._collection.count())
        res = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        out: list[tuple[Chunk, float]] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            chunk = Chunk(
                chunk_id=cid,
                doc_id=meta.get("doc_id", ""),
                text=doc,
                category=meta.get("category", ""),
                title=meta.get("title", ""),
                source=meta.get("source", ""),
                metadata={k: v for k, v in meta.items() if k not in {
                    "doc_id", "category", "title", "source"
                }},
            )
            # Chroma cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1].
            score = max(0.0, 1.0 - float(dist) / 2.0)
            out.append((chunk, score))
        return out

    def count(self) -> int:
        if not self._collection:
            return 0
        return self._collection.count()

    def get_embedder_tag(self) -> str | None:
        if not self._collection:
            return None
        meta = self._collection.metadata or {}
        return meta.get("embedder_tag")

    def set_embedder_tag(self, tag: str) -> None:
        if not self._collection:
            return
        # Preserve the HNSW space setting; just stamp the embedder id.
        meta = dict(self._collection.metadata or {})
        meta["embedder_tag"] = tag
        try:
            self._collection.modify(metadata=meta)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to stamp embedder_tag on collection: %s", exc)

    def clear(self) -> None:
        if not self._client or not self._collection:
            return
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _meta(c: Chunk) -> dict[str, str]:
        meta = {
            "doc_id": c.doc_id,
            "category": c.category,
            "title": c.title,
            "source": c.source,
        }
        meta.update({k: str(v) for k, v in c.metadata.items()})
        return meta


# ---------------------------------------------------------------------------
class InMemoryVectorStore(VectorStore):
    """Pure-Python cosine-similarity store (no external deps)."""

    name = "inmemory"

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []
        self._embedder_tag: str | None = None

    def get_embedder_tag(self) -> str | None:
        return self._embedder_tag

    def set_embedder_tag(self, tag: str) -> None:
        self._embedder_tag = tag

    def upsert(self, chunks: list[Chunk]) -> None:
        existing = {c.chunk_id: i for i, c in enumerate(self._chunks)}
        for c in chunks:
            if c.embedding is None:
                continue
            if c.chunk_id in existing:
                i = existing[c.chunk_id]
                self._chunks[i] = c
                self._vectors[i] = c.embedding
            else:
                self._chunks.append(c)
                self._vectors.append(c.embedding)

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Chunk, float]]:
        if not self._vectors:
            return []
        scored = [
            (chunk, _cosine(query_embedding, vec))
            for chunk, vec in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
        self._vectors.clear()

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)


# ---------------------------------------------------------------------------
def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
def default_vector_store(
    persist_path: str, collection_name: str, prefer_chroma: bool = True
) -> VectorStore:
    """Choose the best available vector store backend.

    Tries ChromaDB first (persistent, survives restarts); falls back to
    the in-memory store so retrieval still works offline.
    """
    if prefer_chroma:
        store = ChromaVectorStore(persist_path, collection_name)
        if store.available:
            return store
        logger.warning("ChromaDB unavailable; falling back to in-memory store.")
    return InMemoryVectorStore()
