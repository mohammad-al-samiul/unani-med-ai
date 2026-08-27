#!/usr/bin/env python3
"""
Semantic Cache Service  (polished v2)
--------------------------------------
- Async-first: uses httpx for all Ollama embedding calls
- Hit/miss counters persisted in-memory (reset on restart)
- TTL-based eviction: entries older than `ttl_days` are pruned on startup and on demand
- Cosine distance → similarity: ChromaDB default is cosine, so similarity = 1 - distance
- Cache-warmup endpoint: POST /warmup accepts a list of question strings
- /cache-stats returns hits, misses, hit_rate, total_entries
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import chromadb
import httpx
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("semantic-cache")

# ── Constants ──────────────────────────────────────────────────────────────────
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"
SIMILARITY_THRESHOLD = 0.92   # cosine similarity (0–1); tune if needed
TTL_DAYS = 30                  # cached entries older than this are pruned
EMBED_TIMEOUT = 15             # seconds


# ── Core service ───────────────────────────────────────────────────────────────
class SemanticCacheService:
    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        ttl_days: int = TTL_DAYS,
    ):
        self.similarity_threshold = similarity_threshold
        self.ttl_days = ttl_days
        self._hits = 0
        self._misses = 0

        self.client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = "semantic_cache"
        self._init_collection()
        self._prune_expired()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _init_collection(self):
        """Get or create cache collection (cosine distance)."""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info("Loaded existing semantic cache collection.")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "description": "Semantic cache for question-answer pairs",
                },
            )
            logger.info("Created new semantic cache collection.")

    def _make_id(self, question: str, patient_context: str = "") -> str:
        """Stable, short ID from question + context."""
        raw = f"{question.strip()}|{patient_context.strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:40]

    async def _embed(self, text: str) -> Optional[List[float]]:
        """Get embedding vector from Ollama (async)."""
        try:
            async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
                resp = await client.post(
                    OLLAMA_EMBED_URL,
                    json={"model": EMBED_MODEL, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding") or data.get("embeddings", [None])[0]
        except Exception as exc:
            logger.warning("Embedding request failed: %s", exc)
            return None

    def _prune_expired(self):
        """Remove entries whose cached_at is older than ttl_days."""
        try:
            cutoff = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()
            all_data = self.collection.get(include=["metadatas"])
            ids_to_delete = [
                id_
                for id_, meta in zip(all_data["ids"], all_data["metadatas"])
                if meta.get("cached_at", "9999") < cutoff
            ]
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info("Pruned %d expired cache entries.", len(ids_to_delete))
        except Exception as exc:
            logger.warning("Cache pruning failed: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def check_cache(
        self, question: str, patient_context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Look up question in cache.
        Returns cached payload if cosine similarity ≥ threshold, else None.
        """
        embedding = await self._embed(question)
        if embedding is None:
            return None

        try:
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=1,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("Cache query error: %s", exc)
            return None

        if not results or not results["distances"][0]:
            self._misses += 1
            return None

        # ChromaDB cosine distance ∈ [0, 2]; similarity = 1 - distance
        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        if similarity >= self.similarity_threshold:
            self._hits += 1
            return {
                "cached": True,
                "similarity": round(similarity, 4),
                "response": results["documents"][0][0],
                "metadata": results["metadatas"][0][0],
                "cached_at": results["metadatas"][0][0].get("cached_at"),
            }

        self._misses += 1
        return None

    async def store_cache(
        self,
        question: str,
        response: str,
        patient_context: str = "",
        extra_metadata: Optional[Dict] = None,
    ) -> bool:
        """Store a question-answer pair in the cache."""
        embedding = await self._embed(question)
        if embedding is None:
            return False

        doc_id = self._make_id(question, patient_context)
        metadata: Dict[str, Any] = {
            "question": question[:500],          # ChromaDB metadata value limit
            "patient_context": patient_context[:200],
            "cached_at": datetime.now().isoformat(),
            "response_length": len(response),
        }
        if extra_metadata:
            # Flatten only scalar values — ChromaDB doesn't accept nested dicts
            for k, v in extra_metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[k] = v

        try:
            # Upsert: replace if same question asked again
            self.collection.upsert(
                embeddings=[embedding],
                documents=[response],
                metadatas=[metadata],
                ids=[doc_id],
            )
            logger.info("Cached response for: %.60s…", question)
            return True
        except Exception as exc:
            logger.error("Cache store error: %s", exc)
            return False

    async def warmup(self, questions: List[str]) -> Dict[str, int]:
        """Pre-embed a list of questions (no answers stored — just warms the embed model)."""
        warmed = 0
        failed = 0
        for q in questions:
            emb = await self._embed(q)
            if emb:
                warmed += 1
            else:
                failed += 1
        return {"warmed": warmed, "failed": failed}

    def clear_cache(self) -> bool:
        """Wipe all cached entries."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._init_collection()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared.")
            return True
        except Exception as exc:
            logger.error("Cache clear error: %s", exc)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics."""
        try:
            total = self.collection.count()
        except Exception:
            total = -1

        total_queries = self._hits + self._misses
        hit_rate = round(self._hits / total_queries, 4) if total_queries else 0.0

        return {
            "total_entries": total,
            "hits": self._hits,
            "misses": self._misses,
            "total_queries": total_queries,
            "hit_rate": hit_rate,
            "similarity_threshold": self.similarity_threshold,
            "ttl_days": self.ttl_days,
            "collection_name": self.collection_name,
        }

    def prune_expired(self) -> Dict[str, int]:
        """Manually trigger TTL-based pruning."""
        before = self.collection.count()
        self._prune_expired()
        after = self.collection.count()
        return {"pruned": before - after, "remaining": after}


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="Semantic Cache Service", version="2.0.0")
cache_service = SemanticCacheService()


class CacheCheckRequest(BaseModel):
    question: str
    patient_context: str = ""


class CacheStoreRequest(BaseModel):
    question: str
    response: str
    patient_context: str = ""
    metadata: Optional[Dict[str, Any]] = None


class WarmupRequest(BaseModel):
    questions: List[str]


@app.post("/check-cache")
async def check_cache(request: CacheCheckRequest):
    """Check if a similar question is cached. Returns cached payload or {cached: false}."""
    result = await cache_service.check_cache(request.question, request.patient_context)
    return result or {"cached": False}


@app.post("/store-cache")
async def store_cache(request: CacheStoreRequest):
    """Store a question-answer pair."""
    success = await cache_service.store_cache(
        request.question,
        request.response,
        request.patient_context,
        request.metadata,
    )
    return {"success": success}


@app.post("/warmup")
async def warmup(request: WarmupRequest):
    """Pre-warm the embedding model with a list of questions."""
    return await cache_service.warmup(request.questions)


@app.post("/clear-cache")
async def clear_cache():
    """Wipe all cache entries and reset counters."""
    return {"success": cache_service.clear_cache()}


@app.post("/prune")
async def prune():
    """Remove entries older than the configured TTL."""
    return cache_service.prune_expired()


@app.get("/cache-stats")
async def cache_stats():
    """Runtime statistics: hits, misses, hit_rate, total_entries."""
    return cache_service.get_stats()


@app.get("/health")
async def health():
    stats = cache_service.get_stats()
    return {
        "status": "healthy",
        "service": "semantic-cache-service",
        "total_entries": stats["total_entries"],
        "hit_rate": stats["hit_rate"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
