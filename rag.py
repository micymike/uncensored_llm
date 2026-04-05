"""
rag.py — Production RAG pipeline for Mimo
Features:
  - Persistent ChromaDB index with dedup by content hash
  - Batched ingestion (avoids OOM on large doc sets)
  - Embedding model singleton (load once, reuse everywhere)
  - Graceful no-index fallback
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("MimoRAG")

# ─── Configuration ────────────────────────────────────────────────────────────
DOCS_ROOT       = Path(os.getenv("RAG_DOCS_PATH",   "python-3.14-docs-text/python-3.14-docs-text"))
CHROMA_PATH     = Path(os.getenv("RAG_CHROMA_PATH", "chroma_db"))
COLLECTION_NAME = os.getenv("RAG_COLLECTION",       "python_docs")
EMBED_MODEL_ID  = os.getenv("RAG_EMBED_MODEL",      "all-MiniLM-L6-v2")
CHUNK_SIZE      = int(os.getenv("RAG_CHUNK_SIZE",   "500"))
CHUNK_OVERLAP   = int(os.getenv("RAG_CHUNK_OVERLAP","80"))
BATCH_SIZE      = int(os.getenv("RAG_BATCH_SIZE",   "256"))

# ─── Singletons ───────────────────────────────────────────────────────────────
_embed_model = None
_chroma_client = None
_collection = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBED_MODEL_ID}")
        _embed_model = SentenceTransformer(EMBED_MODEL_ID)
    return _embed_model


def _get_collection(create: bool = False):
    """Return (or optionally create) the ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
    except ImportError:
        raise ImportError("chromadb not installed. Run: pip install chromadb")

    _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if create:
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
    else:
        try:
            _collection = _chroma_client.get_collection(name=COLLECTION_NAME)
        except Exception:
            raise FileNotFoundError(
                f"RAG index '{COLLECTION_NAME}' not found at {CHROMA_PATH}. "
                "Run build_index() first."
            )
    return _collection


# ─── Text Chunking ────────────────────────────────────────────────────────────
def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Character-level chunker with word-boundary awareness and overlap.
    Much more reliable than the token-counting approach in the original.
    """
    words = text.split()
    chunks: List[str] = []
    start = 0

    while start < len(words):
        end = start
        length = 0
        while end < len(words) and length < chunk_size:
            length += len(words[end]) + 1
            end += 1

        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)

        # Slide back by overlap word-count estimate
        overlap_words = max(1, overlap // 6)
        start = max(start + 1, end - overlap_words)

    return chunks


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ─── Index Builder ────────────────────────────────────────────────────────────
def build_index(
    docs_root: Path = DOCS_ROOT,
    chroma_path: Path = CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
    force_rebuild: bool = False,
) -> None:
    """
    Ingest all .txt files under docs_root into ChromaDB.
    Skips chunks already present (dedup by content hash).
    Processes in batches to stay memory-efficient.
    """
    docs_root = Path(docs_root)
    if not docs_root.exists():
        raise FileNotFoundError(f"Docs root not found: {docs_root}")

    collection = _get_collection(create=True)

    if force_rebuild:
        logger.warning("force_rebuild=True — deleting existing collection data")
        collection.delete(where={"source": {"$ne": "__never__"}})

    # Gather existing IDs to skip
    existing = set(collection.get(include=[])["ids"])
    logger.info(f"Existing chunks in index: {len(existing)}")

    embed_model = _get_embed_model()

    all_files = list(docs_root.rglob("*.txt"))
    logger.info(f"Found {len(all_files)} source files")

    buffer_ids: List[str] = []
    buffer_docs: List[str] = []
    buffer_metas: List[Dict] = []
    buffer_embs: List[List[float]] = []
    total_added = 0

    def flush():
        nonlocal total_added
        if buffer_ids:
            collection.add(
                ids=buffer_ids,
                documents=buffer_docs,
                embeddings=buffer_embs,
                metadatas=buffer_metas,
            )
            total_added += len(buffer_ids)
            logger.info(f"Flushed {len(buffer_ids)} chunks (total: {total_added})")
            buffer_ids.clear(); buffer_docs.clear()
            buffer_metas.clear(); buffer_embs.clear()

    for file_path in all_files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        chunks = split_text(text)
        for chunk in chunks:
            chunk_id = _content_hash(chunk)
            if chunk_id in existing:
                continue    # already indexed

            embedding = embed_model.encode(chunk, convert_to_numpy=True).tolist()
            buffer_ids.append(chunk_id)
            buffer_docs.append(chunk)
            buffer_embs.append(embedding)
            buffer_metas.append({"source": str(file_path.name), "path": str(file_path)})

            if len(buffer_ids) >= BATCH_SIZE:
                flush()

    flush()   # final batch
    logger.info(f"Index build complete. {total_added} new chunks added.")


# ─── Retrieval ────────────────────────────────────────────────────────────────
def retrieve(
    query: str,
    k: int = 5,
    score_threshold: float = 1.5,   # cosine distance; lower = more similar
) -> List[Dict]:
    """
    Retrieve top-k relevant chunks for a query.
    Filters by score_threshold to drop irrelevant matches.
    Returns list of {"path": str, "text": str, "score": float}.
    """
    if not query.strip():
        return []

    collection = _get_collection(create=False)
    embed_model = _get_embed_model()

    query_emb = embed_model.encode(query, convert_to_numpy=True).tolist()

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results.get("documents", [[]])[0]
    metas     = results.get("metadatas",  [[]])[0]
    distances = results.get("distances",  [[]])[0]

    out = []
    for doc, meta, dist in zip(docs, metas, distances):
        if dist <= score_threshold:
            out.append({"path": meta.get("path", ""), "text": doc, "score": round(dist, 4)})

    return out


# ─── CLI helper ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build_index()
    elif cmd == "query" and len(sys.argv) > 2:
        hits = retrieve(" ".join(sys.argv[2:]))
        for h in hits:
            print(f"[{h['score']}] {h['path']}\n{h['text'][:200]}\n")
