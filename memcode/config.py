"""
memcode/config.py
Central configuration — edit here or override via environment variables.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Where ChromaDB stores its data
MEMCODE_DIR = Path(os.getenv("MEMCODE_DIR", Path.home() / ".memcode"))
CHROMA_PATH = MEMCODE_DIR / "chroma"

# How many past memory snippets to inject into each prompt
MEMORY_RESULTS = int(os.getenv("MEMCODE_RESULTS", "5"))

# Similarity threshold (chromadb uses cosine distance: 0=identical, 1=completely different)
# Only include memories with distance below this threshold (more similar = lower distance)
# 0.85 is permissive — short personal queries like "things I love to build" may score
# 0.7+ distance against longer stored facts; the prompt instructs the LLM to filter.
MEMORY_SIMILARITY_THRESHOLD = float(os.getenv("MEMCODE_SIMILARITY_THRESHOLD", "0.85"))

# Max characters of memory context to inject (guards context window)
MEMORY_CONTEXT_LIMIT = int(os.getenv("MEMCODE_CONTEXT_LIMIT", "3000"))

# OpenCode binary name (assumes it's on PATH)
OPENCODE_BIN = os.getenv("OPENCODE_BIN", "opencode")

# Collection name inside ChromaDB
COLLECTION_NAME = "memcode_sessions"

# Ensure dirs exist
MEMCODE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PATH.mkdir(parents=True, exist_ok=True)
