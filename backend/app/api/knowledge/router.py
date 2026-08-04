"""Knowledge base (RAG) API routes.

Endpoints:
  POST   /api/knowledge/search   — semantic + keyword search
  POST   /api/knowledge/ingest   — add a text document to the KB
  GET    /api/knowledge/stats    — KB status (chunk count, backend)
  POST   /api/knowledge/rebuild  — rebuild index from bundled docs
"""
from fastapi import APIRouter

from app.schemas.knowledge import (
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
)
from app.services import knowledge_service

router = APIRouter()


@router.post("/search", response_model=KnowledgeSearchResponse)
def search(payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    result = knowledge_service.search(query=payload.query, top_k=payload.top_k)
    return KnowledgeSearchResponse(**result)


@router.post("/ingest", response_model=KnowledgeIngestResponse)
def ingest(payload: KnowledgeIngestRequest) -> KnowledgeIngestResponse:
    result = knowledge_service.ingest(
        title=payload.title,
        category=payload.category,
        content=payload.content,
        source=payload.source,
    )
    return KnowledgeIngestResponse(**result)


@router.get("/stats", response_model=KnowledgeStatsResponse)
def get_stats() -> KnowledgeStatsResponse:
    return KnowledgeStatsResponse(**knowledge_service.stats())


@router.post("/rebuild")
def rebuild() -> dict:
    return knowledge_service.rebuild()
