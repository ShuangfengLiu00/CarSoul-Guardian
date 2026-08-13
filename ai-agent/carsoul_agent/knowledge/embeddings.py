"""Embedding providers for the RAG knowledge base.

Three-tier strategy so the knowledge base ALWAYS works:

1. ``OpenAIEmbedding``   — best quality, needs ``OPENAI_API_KEY`` + network.
2. ``HashEmbedding``      — deterministic offline fallback, zero deps.
   Tokenises with char-bigrams (great for Chinese) and projects each
   token's hash into a fixed-size vector via the "hashing trick".
   Cosine similarity then approximates lexical overlap — good enough
   for keyword-style queries in offline demos.

The provider is chosen automatically by :func:`default_embedding_provider`.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Fixed dimension for the offline hash embedding. Must be a power of two
# so we can use a bitmask for modulo (cheap). 1024 is a good balance.
_HASH_DIM = 1024


class EmbeddingProvider(ABC):
    """Contract every embedding backend must satisfy."""

    name: str = "base"
    dimension: int = 0

    @property
    def tag(self) -> str:
        """Stable identity string used to detect embedder changes.

        If the configured ``model`` (or provider name) differs from what
        the persisted vector store was built with, the store must be
        re-indexed — otherwise retrieval would silently run against
        stale vectors from a different embedding space.
        """
        model = getattr(self, "_model", None)
        return f"{self.name}:{model}" if model else self.name

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return an L2-normalised embedding for ``text``."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts. Default impl loops; backends may override."""
        return [self.embed(t) for t in texts]


# ---------------------------------------------------------------------------
class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI-compatible embedding API (multilingual, vector search ready).

    Works with any OpenAI-compatible endpoint — OpenAI itself, Azure,
    or China-available providers such as 智谱 (GLM) / 通义千问 / 火山方舟
    — as long as ``base_url`` points at a ``/v1/embeddings``-compatible
    service. The model id is configurable (see ``EMBEDDING_MODEL``) so a
    deployment is not hard-pinned to ``text-embedding-3-small``.
    """

    name = "openai"
    # Dimension depends on the chosen model; resolved lazily after the
    # first call. We default the *declared* dimension to 1536 (the common
    # case for text-embedding-3-small) but always trust the API response.
    dimension = 1536
    _MODEL = "text-embedding-3-small"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url or None
        self._model = model or self._MODEL
        self._client = None
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=api_key, base_url=self._base_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI embedding client init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    # 各家 embedding 接口对单次 input 条数上限不同：
    #   通义 text-embedding-v3 ≤10、智谱 embedding-3 ≤64、OpenAI ≤2048。
    # 取最保守的 10 作为通用安全值，保证任意供应商都不超限；
    # 若切到智谱/OpenAI 想提速，可在此调大（不影响正确性）。
    _BATCH_LIMIT = 10

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._client:
            raise RuntimeError("OpenAI embedding client not available")
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._BATCH_LIMIT):
            batch = texts[i : i + self._BATCH_LIMIT]
            resp = self._client.embeddings.create(model=self._model, input=batch)
            all_embeddings.extend(d.embedding for d in resp.data)
        # Trust the model's real dimension (e.g. 智谱 embedding-3 → 2048).
        if all_embeddings and len(all_embeddings[0]) != self.dimension:
            self.dimension = len(all_embeddings[0])
        return all_embeddings


# ---------------------------------------------------------------------------
class HashEmbedding(EmbeddingProvider):
    """Deterministic offline embedding via the hashing trick.

    Tokenisation mixes word-unigrams (for Latin text / numbers / codes)
    and char-bigrams (for Chinese, where word boundaries are fuzzy).
    Each token is hashed twice (signed) to position + sign, accumulating
    into a fixed vector which is then L2-normalised.
    """

    name = "hash"
    dimension = _HASH_DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * _HASH_DIM
        for token in self._tokenize(text):
            h = hashlib.md5(token.encode("utf-8")).digest()
            # First 4 bytes → position, next 4 bytes → sign.
            pos = int.from_bytes(h[:4], "little") & (_HASH_DIM - 1)
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            vec[pos] += sign
        return self._l2_normalize(vec)

    # -- helpers --------------------------------------------------------
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = text.lower()
        tokens: list[str] = []
        # Word-level tokens (latin words, numbers, codes like P0420).
        for word in re.findall(r"[a-z0-9]+", text):
            tokens.append(word)
            if len(word) > 3:
                # add bigrams inside long latin tokens too
                for i in range(len(word) - 1):
                    tokens.append(word[i : i + 2])
        # Char-bigrams for CJK and general text (captures Chinese phrases).
        chars = re.sub(r"\s+", "", text)
        for i in range(len(chars) - 1):
            tokens.append(chars[i : i + 2])
        # Also single CJK chars (short queries often match on one char).
        for ch in chars:
            if "\u4e00" <= ch <= "\u9fff":
                tokens.append(ch)
        return tokens

    @staticmethod
    def _l2_normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-12:
            return vec
        return [v / norm for v in vec]


# ---------------------------------------------------------------------------
def default_embedding_provider(
    api_key: str = "",
    base_url: str = "",
    model: str | None = None,
) -> EmbeddingProvider:
    """Pick the best available embedding backend.

    Prefers an OpenAI-compatible semantic embedding when a key is configured
    AND the ``openai`` SDK is installed; otherwise falls back to the
    zero-dependency HashEmbedding so the knowledge base is always usable.

    ``model`` selects the embedding model id (defaults to
    ``text-embedding-3-small``). Pass a China-available model id (e.g.
    智谱 ``embedding-3`` / 通义 ``text-embedding-v3``) together with the
    matching ``base_url`` to run true semantic retrieval on local infra.
    """
    if api_key:
        provider = OpenAIEmbedding(
            api_key=api_key, base_url=base_url or None, model=model
        )
        if provider.available:
            logger.info("RAG embedding backend: openai (model=%s)", provider._model)
            return provider
        logger.warning(
            "OpenAI key set but `openai` SDK unavailable; using hash embedding. "
            "Install `openai` to enable true semantic retrieval."
        )
    logger.info("RAG embedding backend: hash (offline, non-semantic)")
    return HashEmbedding()
