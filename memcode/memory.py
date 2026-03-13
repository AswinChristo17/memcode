"""
memcode/memory.py
ChromaDB-backed memory store.
Stores and retrieves past sessions using semantic vector search.
"""
import uuid
import json
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from memcode.config import CHROMA_PATH, COLLECTION_NAME, MEMORY_RESULTS, MEMORY_CONTEXT_LIMIT, MEMORY_SIMILARITY_THRESHOLD


def _get_collection():
    """Return (or create) the ChromaDB collection with a local embedding function."""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    ef = embedding_functions.DefaultEmbeddingFunction()  # uses all-MiniLM-L6-v2 locally
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def store_session(user_message: str, assistant_response: str, metadata: Optional[dict] = None, is_personal: bool = False):
    """
    Store a user/assistant exchange as a memory entry.

    For personal/fact sessions (is_personal=True), the document indexed is just
    the assistant's response (the extracted facts). This ensures that future
    factual queries like "what is my favorite novel?" match the stored facts
    directly, instead of matching the user's conversational phrasing.

    For regular Q&A, the full "User: ...\nAssistant: ..." document is indexed.
    """
    collection = _get_collection()

    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    if is_personal:
        # Combine user message + assistant response for richer embedding coverage.
        # The user message contains the facts as explicitly stated ("my favorite novel
        # is Shadow Slave"), which scores directly against future recall queries.
        # The assistant response adds keyword coverage from the AI's summary.
        document = f"{user_message}\n{assistant_response[:500]}"
    else:
        # Combined text for embedding — richer signal than just the prompt
        document = f"User: {user_message}\nAssistant: {assistant_response}"

    meta = {
        "timestamp": timestamp,
        "user_message": user_message[:500],       # truncate for metadata limits
        "assistant_response": assistant_response[:1000],
        "is_personal": "1" if is_personal else "0",
        **(metadata or {}),
    }

    collection.add(
        documents=[document],
        metadatas=[meta],
        ids=[session_id],
    )

    return session_id


def retrieve_relevant(query: str, n_results: int = MEMORY_RESULTS, threshold: float = MEMORY_SIMILARITY_THRESHOLD) -> list[dict]:
    """
    Retrieve the most semantically relevant past sessions for a given query.
    Only returns results with similarity distance below the threshold.
    Returns a list of dicts with keys: timestamp, user_message, assistant_response, distance.
    """
    collection = _get_collection()

    count = collection.count()
    if count == 0:
        return []

    # Don't ask for more results than we have
    n = min(n_results, count)

    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["metadatas", "distances"],
    )

    memories = []
    for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
        # Only include if below similarity threshold (lower distance = more similar)
        if distance <= threshold:
            memories.append({
                "timestamp": meta.get("timestamp", "unknown"),
                "user_message": meta.get("user_message", ""),
                "assistant_response": meta.get("assistant_response", ""),
                "distance": round(distance, 4),
            })

    # Sort by most recent first among close matches
    memories.sort(key=lambda x: x["timestamp"], reverse=True)
    return memories


def build_memory_context(query: str) -> str:
    """
    Retrieve relevant memories and format them as a context block
    to prepend to the user's prompt. Respects MEMORY_CONTEXT_LIMIT.
    """
    memories = retrieve_relevant(query)
    if not memories:
        return ""

    lines = ["## Relevant context from past sessions\n"]
    total_chars = 0

    for m in memories:
        # Include similarity score in the entry
        similarity = round(1 - m["distance"], 3)  # Convert distance to similarity (0-1)
        entry = (
            f"[{m['timestamp'][:16]}] (similarity: {similarity})\n"
            f"You asked: {m['user_message']}\n"
            f"Summary: {m['assistant_response'][:300]}\n"
            "---\n"
        )
        if total_chars + len(entry) > MEMORY_CONTEXT_LIMIT:
            break
        lines.append(entry)
        total_chars += len(entry)

    if len(lines) == 1:  # only header, nothing fit
        return ""

    lines.append("## Current request\n")
    return "\n".join(lines)


def list_sessions(limit: int = 20) -> list[dict]:
    """Return the most recent N sessions (for `memcode history`)."""
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    results = collection.get(
        limit=min(limit, count),
        include=["metadatas"],
    )

    sessions = []
    for meta in results["metadatas"]:
        sessions.append({
            "timestamp": meta.get("timestamp", ""),
            "user_message": meta.get("user_message", ""),
            "assistant_response": meta.get("assistant_response", ""),
        })

    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return sessions


def clear_all():
    """Wipe the entire memory store."""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    client.delete_collection(COLLECTION_NAME)
