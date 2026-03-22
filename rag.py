import os
from pathlib import Path
import pickle

import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
except ImportError as e:
    raise ImportError("chromadb is required for RAG. Install with pip install chromadb") from e

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise ImportError("sentence-transformers is required for embeddings. Install with pip install sentence-transformers") from e


# Constants
DOCS_ROOT = Path(os.getenv("RAG_DOCS_PATH", "python-3.14-docs-text/python-3.14-docs-text"))
CHROMA_PATH = Path(os.getenv("RAG_CHROMA_PATH", "chroma_db"))
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "python_docs")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", 128))


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    sentences = text.replace("\n", " ").split(" ")
    out = []
    i = 0
    current = []

    while i < len(sentences):
        current.append(sentences[i])
        if len(" ".join(current)) >= chunk_size:
            out.append(" ".join(current))
            i -= overlap // 5 if overlap else 0
            if i < 0:
                i = 0
            current = []
        i += 1

    if current:
        out.append(" ".join(current))

    return out


def get_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')


def build_index(docs_root=DOCS_ROOT, chroma_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    docs_root = Path(docs_root)
    chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    collection = chroma_client.get_or_create_collection(name=collection_name)

    embed_model = get_embedding_model()
    chunks = []
    ids = []

    for idx, p in enumerate(docs_root.rglob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for chunk in split_text(text):
            chunks.append(chunk)
            ids.append(f"{p.name}_{idx}")

    if not chunks:
        raise ValueError(f"No text docs found in {docs_root}")

    embeddings = embed_model.encode(chunks, convert_to_numpy=True)
    collection.add(
        embeddings=embeddings.tolist(),
        documents=chunks,
        ids=ids,
        metadatas=[{"path": str(p)} for p in docs_root.rglob("*.txt") for _ in split_text(p.read_text(encoding="utf-8", errors="ignore"))]
    )

    return collection


def retrieve(query, k=5, chroma_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except ValueError:
        raise FileNotFoundError("RAG index not found. Run build_index() first.")

    embed_model = get_embedding_model()
    query_emb = embed_model.encode([query], convert_to_numpy=True)
    results = collection.query(
        query_embeddings=query_emb.tolist(),
        n_results=k
    )

    return [{"path": meta["path"], "text": doc} for meta, doc in zip(results["metadatas"][0], results["documents"][0])]

