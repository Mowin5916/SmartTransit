# rag_api.py
"""
Simple RAG FastAPI service.
- Loads FAISS index + metadata produced by rag_ingest.py (backend/rag_store/)
- Embeds incoming queries with sentence-transformers (all-MiniLM-L6-v2)
- Retrieves top-k passages and optionally calls OpenAI to generate a final answer with citations.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Optional OpenAI usage (only if OPENAI_API_KEY is present)
try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

BASE = Path(__file__).resolve().parent
RAG_DIR = BASE / "rag_store"
INDEX_FILE = RAG_DIR / "faiss_index.bin"
META_FILE = RAG_DIR / "index_meta.json"
MANIFEST_FILE = RAG_DIR / "sources.json"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5

app = FastAPI(title="SmartTransit RAG API")

# Load manifest
if not RAG_DIR.exists():
    raise RuntimeError(f"RAG store directory not found: {RAG_DIR}")

if not INDEX_FILE.exists() or not META_FILE.exists():
    raise RuntimeError("FAISS index or metadata not found. Run rag_ingest.py first.")

with open(META_FILE, "r", encoding="utf-8") as f:
    INDEX_META = json.load(f)

# load optional manifest
MANIFEST = {}
if MANIFEST_FILE.exists():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        MANIFEST = json.load(f)

# Load the FAISS index
_index = faiss.read_index(str(INDEX_FILE))

# Load embedding model
_embed_model = SentenceTransformer(EMBED_MODEL_NAME)

# Configure OpenAI if available and key set
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    # optional: set default model name here
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
else:
    OPENAI_API_KEY = None

class ChatRequest(BaseModel):
    query: str
    top_k: int = DEFAULT_TOP_K

def embed_query(text: str) -> np.ndarray:
    vec = _embed_model.encode([text], convert_to_numpy=True)
    # normalize
    norm = np.linalg.norm(vec, axis=1, keepdims=True)
    norm[norm == 0] = 1
    vec = vec / norm
    return vec.astype("float32")

def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
    qvec = embed_query(query)
    D, I = _index.search(qvec, top_k)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(INDEX_META):
            continue
        meta = INDEX_META[idx]
        results.append({
            "score": float(score),
            "index": int(idx),
            "text": meta.get("text"),
            "meta": meta.get("meta", {}),
            "source": meta.get("source"),
            "chunk_id": meta.get("chunk_id")
        })
    return results

def build_prompt(query: str, retrieved: List[Dict[str, Any]]) -> str:
    """
    Build a simple prompt to pass to the LLM.
    We include top retrieved passages with clear separators and ask for a concise answer with citations.
    """
    prompt_parts = []
    prompt_parts.append("You are SmartTransit Copilot. Use only the provided sources to answer the question.")
    prompt_parts.append(f"Question: {query}")
    prompt_parts.append("Sources:")
    for i, r in enumerate(retrieved, start=1):
        src = r.get("source", "unknown")
        txt = r.get("text", "")
        prompt_parts.append(f"[{i}] Source: {src}\n{txt}\n")
    prompt_parts.append("Instructions: Answer concisely. If information is not present in the sources, say 'I don't know'. When you reference facts, mention the source index in square brackets. Keep answer under 150 words.")
    return "\n\n".join(prompt_parts)

@app.post("/chat")
def chat(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is empty.")

    top_k = max(1, min(20, req.top_k))
    retrieved = retrieve(query, top_k=top_k)

    # Always return retrieved passages as part of the result
    response_payload = {
        "query": query,
        "retrieved": retrieved,
        "answer": None,
        "used_openai": False,
        "note": ""
    }

    # If OpenAI key is present, call LLM for a polished answer
    if OPENAI_API_KEY:
        try:
            prompt = build_prompt(query, retrieved)
            # Use ChatCompletion
            messages = [
                {"role": "system", "content": "You are a helpful assistant that must cite sources from the provided documents."},
                {"role": "user", "content": prompt}
            ]
            chat_resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, max_tokens=300, temperature=0.0)
            text = chat_resp.choices[0].message.get("content", "").strip()
            response_payload["answer"] = text
            response_payload["used_openai"] = True
        except Exception as e:
            response_payload["note"] = f"OpenAI call failed: {e}"
            # fallback to retrieved text concatenation below

    # If no OpenAI or call failed: concatenate retrieved snippets (short)
    if not response_payload["answer"]:
        snippets = []
        for i, r in enumerate(retrieved, start=1):
            snippets.append(f"[{i}] {r.get('text')}")
        answer_text = "\n\n".join(snippets[:5]) if snippets else "No relevant documents found."
        response_payload["answer"] = answer_text
        if not response_payload["note"]:
            response_payload["note"] = "No OpenAI key present; returned retrieved passages."

    return response_payload

@app.get("/rag/sources")
def sources():
    return {"manifest": MANIFEST, "num_chunks": len(INDEX_META)}
