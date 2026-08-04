"""Core data structures for the RAG knowledge base.

These dataclasses flow through every layer (loader → store → retriever →
tool → agent), so they live in one place to avoid circular imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """A source document before chunking."""

    doc_id: str
    source: str  # file path or label
    title: str
    category: str  # e.g. maintenance, fault, battery
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A retrievable text chunk with its own identity."""

    chunk_id: str
    doc_id: str
    text: str
    category: str
    title: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    # Populated by the vector store after embedding.
    embedding: list[float] | None = None


@dataclass
class SearchResult:
    """One hit returned by the retriever."""

    chunk: Chunk
    score: float  # higher is better (cosine similarity or BM25 score)
    backend: str  # "chroma" | "inmemory" | "bm25"


@dataclass
class RetrievalContext:
    """Aggregated context ready to feed into an LLM prompt."""

    query: str
    results: list[SearchResult]
    context_text: str  # pre-formatted, ready to inject into a prompt

    @property
    def is_empty(self) -> bool:
        return not self.results

    def sources(self) -> list[str]:
        """Distinct source labels, preserving order."""
        seen: set[str] = set()
        out: list[str] = []
        for r in self.results:
            if r.chunk.source not in seen:
                seen.add(r.chunk.source)
                out.append(r.chunk.source)
        return out
