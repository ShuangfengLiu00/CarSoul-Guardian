"""Document loading & chunking for the RAG knowledge base.

Reads Markdown files from a docs directory, extracts the title and
category from front-matter-ish headers, then splits each document into
overlapping, semantically-coherent chunks (one per ``##`` section, with
paragraph-level sub-chunks for long sections).
"""
from __future__ import annotations

import logging
import os
import re
from typing import Iterable

from carsoul_agent.knowledge.base import Chunk, Document

logger = logging.getLogger(__name__)

# Roughly 300-500 Chinese characters per chunk — small enough for precise
# retrieval, large enough to carry a complete idea.
_DEFAULT_CHUNK_SIZE = 400
_DEFAULT_OVERLAP = 80


class MarkdownLoader:
    """Load ``.md`` files into :class:`Document` objects."""

    @staticmethod
    def load_dir(directory: str) -> list[Document]:
        docs: list[Document] = []
        if not os.path.isdir(directory):
            logger.warning("Knowledge docs directory not found: %s", directory)
            return docs
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith((".md", ".markdown", ".txt")):
                continue
            path = os.path.join(directory, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except OSError as exc:
                logger.warning("Cannot read %s: %s", path, exc)
                continue
            docs.append(MarkdownLoader.parse(path, fname, content))
        logger.info("Loaded %d knowledge documents from %s", len(docs), directory)
        return docs

    @staticmethod
    def load_text(
        title: str, category: str, content: str, source: str = "inline"
    ) -> Document:
        """Build a Document from raw text (for ad-hoc ingestion)."""
        doc_id = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "doc"
        return Document(
            doc_id=doc_id,
            source=source,
            title=title,
            category=category,
            content=content,
        )

    @staticmethod
    def parse(path: str, fname: str, content: str) -> Document:
        title, category = MarkdownLoader._extract_meta(content, fname)
        doc_id = os.path.splitext(fname)[0]
        return Document(
            doc_id=doc_id,
            source=fname,
            title=title,
            category=category,
            content=content,
        )

    @staticmethod
    def _extract_meta(content: str, fname: str) -> tuple[str, str]:
        title = os.path.splitext(fname)[0]
        category = "general"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                title = stripped[2:].strip()
                continue
            # The "> 类别：xxx" blockquote line carries the category.
            m = re.match(r">\s*类别[:：]\s*(.+)", stripped)
            if m:
                category = m.group(1).split("·")[0].strip()
                break
        return title, category


class TextChunker:
    """Split a Document into retrievable Chunks.

    Strategy:
    1. Split on ``##`` (H2) headings so each chunk stays within one section.
    2. If a section is longer than ``chunk_size``, further split on
       paragraphs / newlines with ``overlap`` characters of carry-over.
    3. Every chunk inherits the document's title, category, source, and
       gains a ``heading`` metadata field when one is available.
    """

    def __init__(
        self, chunk_size: int = _DEFAULT_CHUNK_SIZE, overlap: int = _DEFAULT_OVERLAP
    ) -> None:
        self._size = max(120, chunk_size)
        self._overlap = max(0, min(overlap, self._size // 2))

    def chunk(self, doc: Document) -> list[Chunk]:
        sections = self._split_sections(doc.content)
        chunks: list[Chunk] = []
        idx = 0
        for heading, body in sections:
            body = body.strip()
            if not body:
                continue
            for piece in self._split_long(body, self._size, self._overlap):
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc.doc_id}#{idx}",
                        doc_id=doc.doc_id,
                        text=piece,
                        category=doc.category,
                        title=doc.title,
                        source=doc.source,
                        metadata={"heading": heading} if heading else {},
                    )
                )
                idx += 1
        return chunks

    def chunk_many(self, docs: Iterable[Document]) -> list[Chunk]:
        out: list[Chunk] = []
        for d in docs:
            out.extend(self.chunk(d))
        return out

    # -- internals ------------------------------------------------------
    @staticmethod
    def _split_sections(content: str) -> list[tuple[str, str]]:
        """Return ``[(heading, body), ...]`` split on ``##`` headings."""
        sections: list[tuple[str, str]] = []
        current_heading = ""
        current_body: list[str] = []
        for line in content.splitlines():
            if line.lstrip().startswith("## "):
                if current_body:
                    sections.append((current_heading, "\n".join(current_body)))
                current_heading = line.lstrip()[3:].strip()
                current_body = []
            else:
                current_body.append(line)
        if current_body:
            sections.append((current_heading, "\n".join(current_body)))
        return sections

    @staticmethod
    def _split_long(text: str, size: int, overlap: int) -> list[str]:
        text = text.strip()
        if len(text) <= size:
            return [text]
        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = start + size
            # Try to break on a paragraph / line boundary for readability.
            if end < len(text):
                boundary = text.rfind("\n", start, end)
                if boundary > start + size // 2:
                    end = boundary
            pieces.append(text[start:end].strip())
            if end >= len(text):
                break
            start = end - overlap if overlap else end
        return [p for p in pieces if p]
