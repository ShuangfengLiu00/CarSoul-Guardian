"""Tests for Step 7 — Knowledge Base Expansion.

Covers:
  - YAML loader loads all repair cases & failure patterns
  - Total entry count ≥ 50 (acceptance criterion)
  - Each entry has required fields (id, symptom, system, root_cause,
    recommended_action, confidence)
  - Documents are convertible to Chunks for the RAG pipeline
  - KnowledgeBase auto-loads YAML entries on init
  - Retrieval returns relevant YAML entries for symptom queries
  - Stats report includes yaml_entry_count
"""
import sys
from pathlib import Path

# Make the package importable when running tests directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carsoul_agent.knowledge import (  # noqa: E402
    KnowledgeBase,
    MarkdownLoader,
    TextChunker,
    YamlKnowledgeLoader,
    reset_knowledge_base,
)
from carsoul_agent.knowledge.store import InMemoryVectorStore  # noqa: E402
from carsoul_agent.knowledge.embeddings import HashEmbedding  # noqa: E402


# ------------------------------------------------------------------ #
#  YAML Loader Tests
# ------------------------------------------------------------------ #
def test_yaml_loader_loads_repair_cases():
    """YamlKnowledgeLoader loads repair cases from YAML files."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_repair_cases()
    assert len(docs) >= 30, f"Expected ≥30 repair cases, got {len(docs)}"
    for doc in docs:
        assert doc.metadata.get("entry_type") == "repair_case"
        assert doc.doc_id  # non-empty id
        assert doc.content  # non-empty content


def test_yaml_loader_loads_failure_patterns():
    """YamlKnowledgeLoader loads failure patterns from YAML files."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_failure_patterns()
    assert len(docs) >= 25, f"Expected ≥25 failure patterns, got {len(docs)}"
    for doc in docs:
        assert doc.metadata.get("entry_type") == "failure_pattern"
        assert doc.doc_id
        assert doc.content


def test_yaml_loader_total_entries_meets_threshold():
    """Total YAML entries ≥ 50 (Step 7 acceptance criterion)."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    total = YamlKnowledgeLoader.count_entries(docs)
    assert total >= 50, f"Expected ≥50 total entries, got {total}"


def test_yaml_entries_have_required_fields():
    """Each YAML entry must have id, symptom, system, root_cause, action."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    assert docs, "No YAML entries loaded"
    required_fields = ["id", "symptom", "system", "root_cause",
                       "recommended_action", "confidence"]
    for doc in docs:
        meta = doc.metadata
        for field in required_fields:
            assert field in meta, f"Entry {doc.doc_id} missing field '{field}'"
            assert meta[field] is not None, (
                f"Entry {doc.doc_id} has None for '{field}'"
            )


def test_yaml_entries_have_valid_confidence():
    """Confidence values are between 0 and 1."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    for doc in docs:
        conf = doc.metadata["confidence"]
        assert 0.0 <= conf <= 1.0, (
            f"Entry {doc.doc_id} confidence {conf} out of [0, 1]"
        )


def test_yaml_entries_cover_multiple_systems():
    """YAML entries cover at least 4 distinct vehicle systems."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    systems = {doc.metadata["system"] for doc in docs}
    assert len(systems) >= 4, (
        f"Expected ≥4 systems, got {len(systems)}: {systems}"
    )


def test_yaml_documents_are_chunkable():
    """YAML Document objects can be chunked by TextChunker."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    chunker = TextChunker()
    chunks = chunker.chunk_many(docs)
    assert len(chunks) >= len(docs), (
        "Each document should produce ≥1 chunk"
    )
    for chunk in chunks:
        assert chunk.text
        assert chunk.doc_id
        assert chunk.category


def test_yaml_content_contains_symptom_and_action():
    """Rendered content includes symptom and recommended_action text."""
    loader = YamlKnowledgeLoader()
    docs = loader.load_all()
    for doc in docs:
        symptom = doc.metadata["symptom"]
        action = doc.metadata["recommended_action"]
        assert symptom in doc.content, (
            f"Entry {doc.doc_id} content missing symptom text"
        )
        assert action in doc.content, (
            f"Entry {doc.doc_id} content missing action text"
        )


# ------------------------------------------------------------------ #
#  KnowledgeBase Auto-Load Tests
# ------------------------------------------------------------------ #
def _make_test_kb() -> KnowledgeBase:
    """Create a fresh KnowledgeBase with in-memory store for testing."""
    reset_knowledge_base()
    store = InMemoryVectorStore()
    embedder = HashEmbedding()
    return KnowledgeBase(
        store=store,
        embedder=embedder,
        auto_load=False,
    )


def test_kb_auto_loads_yaml_entries():
    """KnowledgeBase loads YAML entries on first use."""
    kb = _make_test_kb()
    assert kb._yaml_count == 0  # not loaded yet
    kb._ensure_loaded()
    assert kb._yaml_count >= 50, (
        f"Expected ≥50 YAML entries loaded, got {kb._yaml_count}"
    )


def test_kb_stats_includes_yaml_count():
    """Stats dict includes yaml_entry_count."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    stats = kb.stats()
    assert "yaml_entry_count" in stats
    assert stats["yaml_entry_count"] >= 50


def test_kb_chunk_count_includes_yaml():
    """Total chunk count includes both markdown docs and YAML entries."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    # YAML entries (62) + markdown doc chunks (≥9 docs, each ≥1 chunk)
    assert kb.chunk_count >= 60, (
        f"Expected ≥60 total chunks, got {kb.chunk_count}"
    )


def test_kb_rebuild_includes_yaml():
    """rebuild() re-indexes both markdown and YAML knowledge."""
    kb = _make_test_kb()
    n = kb.rebuild()
    assert n >= 60, f"Expected ≥60 chunks after rebuild, got {n}"
    assert kb._yaml_count >= 50


# ------------------------------------------------------------------ #
#  Retrieval Tests — YAML entries discoverable via search
# ------------------------------------------------------------------ #
def test_retrieval_finds_battery_symptom():
    """Searching for a battery symptom returns a relevant YAML entry."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    results = kb.search("充电速度下降 电池温度", top_k=5)
    assert results, "No search results for battery symptom query"
    # At least one result should be from a battery YAML entry
    found_battery = any(
        "battery" in r.chunk.category or "电池" in r.chunk.text
        for r in results
    )
    assert found_battery, "No battery-related result in top-5"


def test_retrieval_finds_motor_symptom():
    """Searching for a motor symptom returns a relevant YAML entry."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    results = kb.search("电机异响 过热", top_k=5)
    assert results, "No search results for motor symptom query"
    found_motor = any(
        "motor" in r.chunk.category or "电机" in r.chunk.text
        for r in results
    )
    assert found_motor, "No motor-related result in top-5"


def test_retrieval_finds_chassis_symptom():
    """Searching for a chassis symptom returns a relevant YAML entry."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    results = kb.search("轮胎 胎压 刹车", top_k=5)
    assert results, "No search results for chassis symptom query"
    found_chassis = any(
        "chassis" in r.chunk.category
        or "轮胎" in r.chunk.text
        or "刹车" in r.chunk.text
        for r in results
    )
    assert found_chassis, "No chassis-related result in top-5"


def test_retrieval_finds_failure_pattern():
    """Searching for a failure pattern returns a relevant YAML entry."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    results = kb.search("热失控 电芯", top_k=5)
    assert results, "No search results for thermal runaway query"
    found_pattern = any(
        "failure_pattern" in r.chunk.category
        or "热失控" in r.chunk.text
        for r in results
    )
    assert found_pattern, "No failure pattern result in top-5"


def test_retrieval_context_includes_yaml_sources():
    """retrieve() context text includes YAML entry sources."""
    kb = _make_test_kb()
    kb._ensure_loaded()
    ctx = kb.retrieve("电池衰减 续航下降", top_k=5)
    assert not ctx.is_empty, "Retrieval context should not be empty"
    assert ctx.context_text, "Context text should be non-empty"
    # The context text should contain knowledge results
    assert "知识库检索结果" in ctx.context_text


# ------------------------------------------------------------------ #
#  Automotive Docs Migration Test
# ------------------------------------------------------------------ #
def test_automotive_docs_directory_has_documents():
    """automotive_docs/ contains ≥9 markdown documents."""
    docs = MarkdownLoader.load_dir(
        str(Path(__file__).resolve().parent.parent
            / "carsoul_agent" / "knowledge" / "automotive_docs")
    )
    assert len(docs) >= 9, f"Expected ≥9 automotive docs, got {len(docs)}"
    for doc in docs:
        assert doc.content
        assert doc.title
