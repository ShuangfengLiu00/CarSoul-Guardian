#!/usr/bin/env python
"""CarSoul Guardian — RAG knowledge base build / inspect CLI (TASK009).

Usage:

    # Build (or rebuild) the vector index from bundled Markdown docs.
    python scripts/build_knowledge_base.py build

    # Inspect the index status.
    python scripts/build_knowledge_base.py stats

    # Run a test query against the knowledge base.
    python scripts/build_knowledge_base.py search "刹车片多久换一次"

    # Ingest an extra Markdown/text file into the knowledge base.
    python scripts/build_knowledge_base.py ingest path/to/notes.md --title "我的笔记" --category 杂谈

Run from the ``ai-agent`` directory so the ``carsoul_agent`` package is
importable, or set ``PYTHONPATH`` accordingly.
"""
from __future__ import annotations

import argparse
import os
import sys

# Ensure the carsoul_agent package is importable when run as a script.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from carsoul_agent.config import settings  # noqa: E402
from carsoul_agent.knowledge import (  # noqa: E402
    MarkdownLoader,
    TextChunker,
    get_knowledge_base,
    reset_knowledge_base,
)


def cmd_build(args: argparse.Namespace) -> int:
    print("Building RAG knowledge base index...")
    reset_knowledge_base()
    kb = get_knowledge_base(
        persist_path=settings.vector_db_path,
        collection_name=settings.chroma_collection,
        api_key=settings.openai_api_key,
        api_base=settings.openai_api_base,
    )
    n = kb.rebuild()
    stats = kb.stats()
    print(f"\n✓ Knowledge base built successfully.")
    print(f"  Chunks indexed : {n}")
    print(f"  Vector backend : {stats['backend']}")
    print(f"  Embedder       : {stats['embedder']}")
    print(f"  Docs directory : {stats['docs_dir']}")
    if stats["backend"] == "inmemory":
        print("\n  ℹ  Using in-memory store (ChromaDB not installed).")
        print("     The index is rebuilt on every startup. Install chromadb")
        print("     for persistence:  pip install chromadb==0.5.3")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    kb = get_knowledge_base(
        persist_path=settings.vector_db_path,
        collection_name=settings.chroma_collection,
        api_key=settings.openai_api_key,
        api_base=settings.openai_api_base,
    )
    stats = kb.stats()
    print("CarSoul Guardian — RAG Knowledge Base Status")
    print("=" * 48)
    for k, v in stats.items():
        print(f"  {k:<16}: {v}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    kb = get_knowledge_base(
        persist_path=settings.vector_db_path,
        collection_name=settings.chroma_collection,
        api_key=settings.openai_api_key,
        api_base=settings.openai_api_base,
    )
    top_k = args.top_k
    results = kb.search(args.query, top_k=top_k)
    if not results:
        print(f"No results for: {args.query}")
        return 1
    print(f"Search: {args.query}")
    print(f"Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        c = r.chunk
        heading = c.metadata.get("heading", "")
        title = c.title + (f" · {heading}" if heading else "")
        print(f"[{i}] {title}  (score={r.score:.3f}, backend={r.backend})")
        print(f"    category={c.category}  source={c.source}")
        preview = c.text.replace("\n", " ")[:120]
        print(f"    {preview}...")
        print()
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    path = args.file
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return 1
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    kb = get_knowledge_base(
        persist_path=settings.vector_db_path,
        collection_name=settings.chroma_collection,
        api_key=settings.openai_api_key,
        api_base=settings.openai_api_base,
    )
    source = os.path.basename(path)
    n = kb.ingest_text(
        title=args.title or source,
        category=args.category or "general",
        content=content,
        source=source,
    )
    print(f"✓ Ingested '{source}' → {n} chunks added.")
    print(f"  Total chunks now: {kb.chunk_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CarSoul Guardian RAG knowledge base CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="Build/rebuild the vector index from docs.")
    sub.add_parser("stats", help="Show knowledge base status.")

    p_search = sub.add_parser("search", help="Search the knowledge base.")
    p_search.add_argument("query", help="Search query text.")
    p_search.add_argument("-k", "--top-k", type=int, default=5, help="Top-K results.")

    p_ingest = sub.add_parser("ingest", help="Ingest an extra document file.")
    p_ingest.add_argument("file", help="Path to a .md/.txt file to ingest.")
    p_ingest.add_argument("--title", default="", help="Document title.")
    p_ingest.add_argument("--category", default="general", help="Document category.")

    args = parser.parse_args()
    handlers = {
        "build": cmd_build,
        "stats": cmd_stats,
        "search": cmd_search,
        "ingest": cmd_ingest,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
