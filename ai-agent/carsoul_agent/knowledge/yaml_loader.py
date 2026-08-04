"""YAML loader for structured repair cases & failure patterns.

Reads ``.yaml`` files from ``repair_cases/`` and ``failure_patterns/``
directories, converts each structured entry into a :class:`Document` that
the existing RAG pipeline (chunker → embedder → store → retriever) can
ingest without modification.

Each YAML file is a list of dicts with a common schema:

    - id: RC-BAT-001
      symptom: 充电速度下降20%
      system: battery
      root_cause: 电芯衰减早期
      recommended_action: 降低快充比例
      confidence: 0.85
      stage: 早期          # optional (failure_patterns only)

The loader renders each entry into a human-readable text block so that
both vector (semantic) and BM25 (keyword) retrieval can match on the
symptom, root cause, and recommended action.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import yaml

from carsoul_agent.knowledge.base import Document

logger = logging.getLogger(__name__)

# Directories bundled with the package.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPAIR_DIR = os.path.join(_THIS_DIR, "repair_cases")
DEFAULT_PATTERNS_DIR = os.path.join(_THIS_DIR, "failure_patterns")


class YamlKnowledgeLoader:
    """Load structured YAML knowledge entries into ``Document`` objects."""

    def __init__(
        self,
        repair_dir: str | None = None,
        patterns_dir: str | None = None,
    ) -> None:
        self._repair_dir = repair_dir or DEFAULT_REPAIR_DIR
        self._patterns_dir = patterns_dir or DEFAULT_PATTERNS_DIR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_all(self) -> list[Document]:
        """Load repair cases + failure patterns, return as Documents."""
        docs = self.load_repair_cases()
        docs.extend(self.load_failure_patterns())
        logger.info(
            "YamlKnowledgeLoader: loaded %d documents "
            "(repair_cases + failure_patterns)",
            len(docs),
        )
        return docs

    def load_repair_cases(self) -> list[Document]:
        """Load all repair-case YAML files from the repair directory."""
        return self._load_dir(self._repair_dir, entry_type="repair_case")

    def load_failure_patterns(self) -> list[Document]:
        """Load all failure-pattern YAML files from the patterns directory."""
        return self._load_dir(self._patterns_dir, entry_type="failure_pattern")

    @staticmethod
    def count_entries(docs: list[Document]) -> int:
        """Count individual knowledge entries (one Document per entry)."""
        return len(docs)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_dir(self, directory: str, entry_type: str) -> list[Document]:
        if not os.path.isdir(directory):
            logger.warning("YAML knowledge directory not found: %s", directory)
            return []

        docs: list[Document] = []
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(directory, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    entries = yaml.safe_load(fh)
            except (OSError, yaml.YAMLError) as exc:
                logger.warning("Cannot read YAML %s: %s", path, exc)
                continue
            if not entries or not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                doc = self._entry_to_document(entry, fname, entry_type)
                if doc:
                    docs.append(doc)
        logger.info(
            "Loaded %d %s entries from %s", len(docs), entry_type, directory
        )
        return docs

    @staticmethod
    def _entry_to_document(
        entry: dict[str, Any], source_file: str, entry_type: str
    ) -> Document | None:
        """Convert a single YAML dict to a searchable Document."""
        entry_id = entry.get("id", "unknown")
        symptom = entry.get("symptom", "")
        system = entry.get("system", "")
        root_cause = entry.get("root_cause", "")
        action = entry.get("recommended_action", "")
        confidence = entry.get("confidence", 0.0)
        stage = entry.get("stage", "")

        if not symptom:
            return None

        # Render a human-readable text block for retrieval.
        lines: list[str] = []
        if entry_type == "repair_case":
            lines.append(f"# 维修案例 {entry_id}")
        else:
            lines.append(f"# 故障模式 {entry_id}")
        lines.append(f"系统：{system}")
        lines.append(f"症状：{symptom}")
        lines.append(f"根因：{root_cause}")
        lines.append(f"建议措施：{action}")
        lines.append(f"置信度：{confidence}")
        if stage:
            lines.append(f"阶段：{stage}")
        content = "\n".join(lines)

        category = f"{system}_{entry_type}"
        doc_id = entry_id

        return Document(
            doc_id=doc_id,
            source=f"{source_file}#{entry_id}",
            title=f"{system} - {entry_type} - {entry_id}",
            category=category,
            content=content,
            metadata={
                "entry_type": entry_type,
                "system": system,
                "symptom": symptom,
                "root_cause": root_cause,
                "recommended_action": action,
                "confidence": confidence,
                "stage": stage,
                "id": entry_id,
            },
        )
