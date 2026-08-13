"""Knowledge base service — thin adapter to the carsoul_agent RAG module.

Same pattern as ``agent_service``: this is the ONLY place the API layer
touches the RAG knowledge base, keeping the architecture modular. The
service lazily loads the shared ``KnowledgeBase`` singleton so the index
is built once per process and reused by every request.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_kb = None


def _load_kb():
    """Lazily import and build the shared knowledge base singleton."""
    global _kb
    if _kb is not None:
        return _kb
    try:
        from carsoul_agent.knowledge import get_knowledge_base

        _kb = get_knowledge_base(
            persist_path=settings.VECTOR_DB_PATH,
            collection_name=settings.CHROMA_COLLECTION,
            api_key=settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY,
            api_base=settings.EMBEDDING_API_BASE or settings.OPENAI_API_BASE,
            model=settings.EMBEDDING_MODEL,
        )
        logger.info("RAG knowledge base loaded (backend=%s).", _kb.backend)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Knowledge base unavailable: %s", exc)
        _kb = None
    return _kb


def search(query: str, top_k: int = 5) -> dict:
    """Search the knowledge base and return ranked chunks + formatted context."""
    kb = _load_kb()
    if kb is None:
        return {
            "query": query,
            "results": [],
            "count": 0,
            "context": "",
            "stats": {"ready": False, "backend": "unavailable"},
            "message": "知识库暂不可用",
        }
    ctx = kb.retrieve(query, top_k=top_k)
    results = [
        {
            "title": r.chunk.title,
            "heading": r.chunk.metadata.get("heading", ""),
            "category": r.chunk.category,
            "source": r.chunk.source,
            "score": r.score,
            "backend": r.backend,
            "text": r.chunk.text,
        }
        for r in ctx.results
    ]
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "context": ctx.context_text,
        "stats": kb.stats(),
    }


def ingest(title: str, category: str, content: str, source: str = "api") -> dict:
    """Ingest a single text document into the knowledge base."""
    kb = _load_kb()
    if kb is None:
        return {
            "title": title,
            "chunks_added": 0,
            "total_chunks": 0,
            "message": "知识库暂不可用，无法导入",
        }
    added = kb.ingest_text(title=title, category=category, content=content, source=source)
    return {
        "title": title,
        "chunks_added": added,
        "total_chunks": kb.chunk_count,
        "message": f"成功导入 {added} 个知识片段",
    }


def stats() -> dict:
    """Return knowledge base status."""
    kb = _load_kb()
    if kb is None:
        return {
            "chunk_count": 0,
            "backend": "unavailable",
            "embedder": "none",
            "embedder_model": "",
            "semantic": False,
            "docs_dir": "",
            "ready": False,
        }
    return kb.stats()


def rebuild() -> dict:
    """Rebuild the index from the bundled docs directory."""
    kb = _load_kb()
    if kb is None:
        return {"chunks": 0, "message": "知识库暂不可用"}
    n = kb.rebuild()
    return {"chunks": n, "message": f"知识库已重建，共 {n} 个片段", "stats": kb.stats()}
