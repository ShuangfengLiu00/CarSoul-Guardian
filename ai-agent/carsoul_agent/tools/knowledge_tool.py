"""RAG knowledge-base tools.

These tools let the agent (and any LLM driving it) query the car
knowledge base. They are read-only and degrade gracefully: if the
knowledge base has no embeddings, the hybrid retriever still answers
via BM25 keyword matching, so the agent is never left without context.

Tools:
  - ``search_knowledge_base`` — semantic + keyword search over curated
    car-care knowledge (maintenance, faults, EV battery, driving, …).
  - ``knowledge_base_stats`` — quick introspection (chunk count, backend).
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.tools.base import BaseTool, ToolResult, default_registry

logger = logging.getLogger(__name__)


class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = (
        "在汽车知识库中检索与用户问题相关的专业知识（保养、故障诊断、新能源电池、"
        "驾驶技巧、轮胎刹车、保险法规、新车/二手车等）。返回最相关的知识片段及来源，"
        "用于辅助回答用户的专业用车问题。"
    )
    parameters = {
        "query": "string  检索问题或关键词，例如「刹车片多久换一次」",
        "top_k": "integer  返回结果数量，默认5",
    }

    def __init__(self, top_k: int = 5) -> None:
        self._default_top_k = top_k
        self._kb = None  # lazy

    @property
    def kb(self):
        """Lazy-load the singleton knowledge base (heavy on first call)."""
        if self._kb is None:
            from carsoul_agent.knowledge import get_knowledge_base

            self._kb = get_knowledge_base()
        return self._kb

    def run(self, query: str = "", top_k: int | None = None, **_: Any) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(ok=False, error="query 不能为空")
        try:
            k = top_k or self._default_top_k
            results = self.kb.search(query, top_k=k)
            if not results:
                return ToolResult(
                    ok=True,
                    data={
                        "query": query,
                        "results": [],
                        "message": "知识库中未找到相关内容",
                    },
                )
            return ToolResult(
                ok=True,
                data={
                    "query": query,
                    "results": [
                        {
                            "title": r.chunk.title,
                            "heading": r.chunk.metadata.get("heading", ""),
                            "category": r.chunk.category,
                            "source": r.chunk.source,
                            "score": r.score,
                            "backend": r.backend,
                            "text": r.chunk.text,
                        }
                        for r in results
                    ],
                    "count": len(results),
                    "context": self.kb.retrieve(query, top_k=k).context_text,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("knowledge search failed: %s", exc)
            return ToolResult(ok=False, error=str(exc))


class KnowledgeBaseStatsTool(BaseTool):
    name = "knowledge_base_stats"
    description = "查看汽车知识库的状态信息（知识片段数量、检索后端、嵌入模型等）。"
    parameters = {}

    def __init__(self) -> None:
        self._kb = None

    @property
    def kb(self):
        if self._kb is None:
            from carsoul_agent.knowledge import get_knowledge_base

            self._kb = get_knowledge_base()
        return self._kb

    def run(self, **_: Any) -> ToolResult:
        try:
            return ToolResult(ok=True, data=self.kb.stats())
        except Exception as exc:  # noqa: BLE001
            logger.exception("knowledge stats failed: %s", exc)
            return ToolResult(ok=False, error=str(exc))


def register_default_tools() -> None:
    """Register knowledge tools into the shared default registry."""
    default_registry.register(SearchKnowledgeBaseTool())
    default_registry.register(KnowledgeBaseStatsTool())


# Register on import so agents discover them out of the box.
register_default_tools()
