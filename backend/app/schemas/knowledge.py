"""Knowledge base (RAG) request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="检索问题或关键词")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")


class KnowledgeChunk(BaseModel):
    title: str
    heading: str = ""
    category: str
    source: str
    score: float
    backend: str
    text: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunk]
    count: int
    context: str = ""
    stats: dict = Field(default_factory=dict, description="知识库状态")


class KnowledgeIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, description="文档标题")
    category: str = Field("general", description="文档类别")
    content: str = Field(..., min_length=1, description="文档内容（纯文本/Markdown）")
    source: str = Field("api", description="来源标识")


class KnowledgeIngestResponse(BaseModel):
    title: str
    chunks_added: int
    total_chunks: int
    message: str = ""


class KnowledgeStatsResponse(BaseModel):
    chunk_count: int
    backend: str
    embedder: str
    docs_dir: str
    ready: bool
