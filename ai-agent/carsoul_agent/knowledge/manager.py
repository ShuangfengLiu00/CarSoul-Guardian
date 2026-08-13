"""KnowledgeBase — the facade that ties the RAG pipeline together.

Responsibilities:
  * Auto-load bundled Markdown docs on first use.
  * Pick the best embedding + store backends available (graceful degrade).
  * Embed, chunk, and index documents (lazy, once).
  * Expose a single ``search()`` / ``retrieve()`` entry point for the
    agent tool and backend API.

The manager is a process-wide singleton via :func:`get_knowledge_base` so
the (potentially heavy) index is built only once and shared by every
caller (agent, API, CLI script).
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Sequence

from carsoul_agent.knowledge.base import (
    Chunk,
    Document,
    RetrievalContext,
    SearchResult,
)
from carsoul_agent.knowledge.embeddings import (
    EmbeddingProvider,
    default_embedding_provider,
)
from carsoul_agent.knowledge.loader import MarkdownLoader, TextChunker
from carsoul_agent.knowledge.retriever import HybridRetriever
from carsoul_agent.knowledge.store import (
    InMemoryVectorStore,
    VectorStore,
    default_vector_store,
)
from carsoul_agent.knowledge.yaml_loader import YamlKnowledgeLoader

logger = logging.getLogger(__name__)

# Default locations of bundled knowledge, relative to this file.
_DEFAULT_DOCS_DIR = os.path.join(os.path.dirname(__file__), "automotive_docs")


class KnowledgeBase:
    """Single entry point for RAG retrieval across the project."""

    def __init__(
        self,
        docs_dir: str | None = None,
        store: VectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
        persist_path: str = "",
        collection_name: str = "carsoul_guardian",
        api_key: str = "",
        api_base: str = "",
        model: str | None = None,
        auto_load: bool = True,
        yaml_loader: YamlKnowledgeLoader | None = None,
    ) -> None:
        self._docs_dir = docs_dir or _DEFAULT_DOCS_DIR
        self._persist_path = persist_path
        self._collection_name = collection_name
        self._embedder = embedder or default_embedding_provider(
            api_key=api_key, base_url=api_base, model=model
        )
        self._store = store or default_vector_store(
            persist_path=persist_path or "./ai-agent/memory/vector_store",
            collection_name=collection_name,
        )
        self._chunker = TextChunker()
        self._retriever = HybridRetriever(self._store, self._embedder)
        self._yaml_loader = yaml_loader or YamlKnowledgeLoader()
        self._loaded = False
        self._lock = threading.Lock()
        self._chunk_count = 0
        self._yaml_count = 0
        if auto_load:
            self._ensure_loaded()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _ensure_loaded(self) -> None:
        """Load + index docs once (idempotent, thread-safe)."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            # If a persistent store already has data (ChromaDB), trust it —
            # BUT only if it was built with the *same* embedder. Switching to
            # a real semantic embedder must invalidate the old (hash) vectors,
            # otherwise we'd silently retrieve in the wrong vector space.
            if self._store.count() == 0:
                docs = MarkdownLoader.load_dir(self._docs_dir)
                # Also load structured YAML knowledge entries.
                yaml_docs = self._yaml_loader.load_all()
                self._yaml_count = len(yaml_docs)
                docs.extend(yaml_docs)
                if docs:
                    self.ingest_documents(docs, show_progress=False)
                self._store.set_embedder_tag(self._embedder.tag)
            else:
                existing = self._store.get_embedder_tag()
                if existing != self._embedder.tag:
                    logger.warning(
                        "Embedder changed (%s -> %s); rebuilding index with "
                        "the new embeddings to avoid stale-vector retrieval.",
                        existing,
                        self._embedder.tag,
                    )
                    self._store.clear()
                    self._store.set_embedder_tag(self._embedder.tag)
                    docs = MarkdownLoader.load_dir(self._docs_dir)
                    yaml_docs = self._yaml_loader.load_all()
                    self._yaml_count = len(yaml_docs)
                    docs.extend(yaml_docs)
                    if docs:
                        self.ingest_documents(docs, show_progress=False)
                    self._chunk_count = self._store.count()
                else:
                    logger.info(
                        "Persistent store already has %d chunks (embedder=%s); "
                        "skipping re-index.",
                        self._store.count(),
                        existing,
                    )
                    self._chunk_count = self._store.count()
            # Always (re)build the in-memory BM25 index from stored chunks
            # so keyword search works regardless of backend.
            self._rebuild_bm25()
            self._loaded = True
            logger.info(
                "KnowledgeBase ready: %d chunks (%d YAML entries), "
                "backend=%s, embedder=%s, semantic=%s",
                self._chunk_count,
                self._yaml_count,
                self._store.name,
                self._embedder.name,
                self._embedder.name != "hash",
            )

    def _rebuild_bm25(self) -> None:
        """Rebuild the BM25 index from the chunks currently in the store."""
        chunks = self._all_chunks()
        if chunks:
            self._retriever.index(chunks)

    def _all_chunks(self) -> list[Chunk]:
        """Materialise all chunks (embeddings stripped for BM25)."""
        if isinstance(self._store, InMemoryVectorStore):
            base = self._store.chunks
            return [
                Chunk(
                    chunk_id=c.chunk_id,
                    doc_id=c.doc_id,
                    text=c.text,
                    category=c.category,
                    title=c.title,
                    source=c.source,
                    metadata=c.metadata,
                )
                for c in base
            ]
        # Chroma path: fetch everything via a dummy query-free scan.
        # ChromaDB has no "get all" in our minimal interface, so we re-load
        # from docs + YAML to rebuild BM25 — cheap and correct.
        docs = MarkdownLoader.load_dir(self._docs_dir)
        docs.extend(self._yaml_loader.load_all())
        return self._chunker.chunk_many(docs)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest_documents(
        self, docs: Sequence[Document], show_progress: bool = True
    ) -> int:
        """Chunk, embed, and store a batch of documents. Returns chunk count."""
        chunks = self._chunker.chunk_many(docs)
        if not chunks:
            return 0
        # Batch-embed for efficiency (OpenAI supports batches).
        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_batch(texts)
        for c, emb in zip(chunks, embeddings):
            c.embedding = emb
        self._store.upsert(chunks)
        self._chunk_count = self._store.count()
        self._retriever.index(chunks)
        if show_progress:
            logger.info("Ingested %d docs → %d chunks", len(docs), len(chunks))
        return len(chunks)

    def ingest_text(
        self, title: str, category: str, content: str, source: str = "inline"
    ) -> int:
        """Convenience: ingest a single text blob."""
        doc = MarkdownLoader.load_text(title, category, content, source)
        return self.ingest_documents([doc])

    def rebuild(self) -> int:
        """Clear the store and re-index everything from the docs dir."""
        self._store.clear()
        self._chunk_count = 0
        docs = MarkdownLoader.load_dir(self._docs_dir)
        # Also load structured YAML knowledge entries.
        yaml_docs = self._yaml_loader.load_all()
        self._yaml_count = len(yaml_docs)
        docs.extend(yaml_docs)
        n = self.ingest_documents(docs) if docs else 0
        self._loaded = True
        return n

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def search(
        self, query: str, top_k: int = 5, min_score: float = 0.05
    ) -> list[SearchResult]:
        """Run hybrid retrieval and return ranked results."""
        self._ensure_loaded()
        if not query.strip():
            return []
        results = self._retriever.search(query, top_k=top_k)
        return [r for r in results if r.score >= min_score]

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalContext:
        """Retrieve and format context ready to inject into an LLM prompt."""
        results = self.search(query, top_k=top_k)
        context_text = self._format_context(query, results)
        return RetrievalContext(query=query, results=results, context_text=context_text)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    @property
    def ready(self) -> bool:
        self._ensure_loaded()
        return self._chunk_count > 0

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    @property
    def backend(self) -> str:
        return self._store.name

    @property
    def embedder_name(self) -> str:
        return self._embedder.name

    def stats(self) -> dict[str, object]:
        self._ensure_loaded()
        return {
            "chunk_count": self._chunk_count,
            "yaml_entry_count": self._yaml_count,
            "backend": self._store.name,
            "embedder": self._embedder.name,
            "embedder_model": getattr(self._embedder, "_model", "")
            or self._embedder.name,
            "semantic": self._embedder.name != "hash",
            "docs_dir": self._docs_dir,
            "ready": self.ready,
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------
    @staticmethod
    def _format_context(query: str, results: list[SearchResult]) -> str:
        if not results:
            return ""
        parts: list[str] = [f"【检索查询】{query}", "【知识库检索结果】"]
        for i, r in enumerate(results, 1):
            c = r.chunk
            heading = c.metadata.get("heading", "")
            header = f"[{i}] 来源：{c.title}"
            if heading:
                header += f" · {heading}"
            header += f"（相关度 {r.score:.2f}，类别：{c.category}）"
            parts.append(header)
            parts.append(c.text)
        parts.append("【请基于以上检索知识回答用户问题，并标注来源】")
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------
_kb_instance: KnowledgeBase | None = None
_kb_lock = threading.Lock()


def get_knowledge_base(
    docs_dir: str | None = None,
    persist_path: str = "",
    collection_name: str = "carsoul_guardian",
    api_key: str = "",
    api_base: str = "",
    model: str | None = None,
) -> KnowledgeBase:
    """Return the shared KnowledgeBase singleton (lazy, thread-safe).

    Subsequent calls return the same instance; configuration arguments are
    only honoured on the very first call.
    """
    global _kb_instance
    if _kb_instance is None:
        with _kb_lock:
            if _kb_instance is None:
                _kb_instance = KnowledgeBase(
                    docs_dir=docs_dir,
                    persist_path=persist_path,
                    collection_name=collection_name,
                    api_key=api_key,
                    api_base=api_base,
                    model=model,
                )
    return _kb_instance


def reset_knowledge_base() -> None:
    """Drop the singleton (used by tests / rebuild scripts)."""
    global _kb_instance
    with _kb_lock:
        _kb_instance = None
