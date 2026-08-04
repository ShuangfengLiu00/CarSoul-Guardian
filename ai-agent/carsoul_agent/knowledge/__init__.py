"""CarSoul Guardian RAG knowledge base package.

Public API:

    from carsoul_agent.knowledge import get_knowledge_base

    kb = get_knowledge_base()
    ctx = kb.retrieve("新能源车冬季续航下降怎么办？")
    print(ctx.context_text)
    print(kb.stats())

Architecture (three-tier graceful degradation):

    ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐
    │ Embeddings   │   │ Vector Store    │   │ Retriever        │
    │ OpenAI → Hash│   │ ChromaDB → Mem  │   │ Hybrid(Vec+BM25) │
    └──────┬───────┘   └────────┬────────┘   └────────┬─────────┘
           └────────────────────┴─────────────────────┘
                            KnowledgeBase (facade)
"""
from carsoul_agent.knowledge.base import (
    Chunk,
    Document,
    RetrievalContext,
    SearchResult,
)
from carsoul_agent.knowledge.embeddings import (
    EmbeddingProvider,
    HashEmbedding,
    OpenAIEmbedding,
    default_embedding_provider,
)
from carsoul_agent.knowledge.loader import MarkdownLoader, TextChunker
from carsoul_agent.knowledge.manager import (
    KnowledgeBase,
    get_knowledge_base,
    reset_knowledge_base,
)
from carsoul_agent.knowledge.retriever import (
    BM25Retriever,
    HybridRetriever,
    VectorRetriever,
)
from carsoul_agent.knowledge.store import (
    ChromaVectorStore,
    InMemoryVectorStore,
    VectorStore,
    default_vector_store,
)
from carsoul_agent.knowledge.yaml_loader import YamlKnowledgeLoader

__all__ = [
    # Data structures
    "Chunk",
    "Document",
    "RetrievalContext",
    "SearchResult",
    # Embeddings
    "EmbeddingProvider",
    "HashEmbedding",
    "OpenAIEmbedding",
    "default_embedding_provider",
    # Store
    "VectorStore",
    "ChromaVectorStore",
    "InMemoryVectorStore",
    "default_vector_store",
    # Loader
    "MarkdownLoader",
    "TextChunker",
    # YAML Loader
    "YamlKnowledgeLoader",
    # Retriever
    "BM25Retriever",
    "VectorRetriever",
    "HybridRetriever",
    # Manager
    "KnowledgeBase",
    "get_knowledge_base",
    "reset_knowledge_base",
]
