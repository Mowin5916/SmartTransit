# rag_ingest.py
"""
RAG ingestion script.
- Reads CSVs from backend/data/
- Converts rows to short human-friendly text documents
- Chunks long texts
- Embeds with sentence-transformers (all-MiniLM-L6-v2)
- Builds a FAISS IndexFlatIP index and saves index + metadata to backend/rag_store/
"""
from pathlib import Path
import json
import math
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import sys

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUT_DIR = BASE / "rag_store"
OUT_DIR.mkdir(exist_ok=True)

# Source files (you have these in backend/data/)
ALERTS_F = DATA_DIR / "alerts_updated.csv"
STOPS_F = DATA_DIR / "bus_stops.csv.csv"
# optional extras (will be ingested if present)
EXTRA_FILES = [
    DATA_DIR / "predictions_updated.csv",
    DATA_DIR / "merged_cleaned.csv",
    DATA_DIR / "bangalore_weather_clean.csv"
]

EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_WORDS = 150
CHUNK_OVERLAP = 25
TOP_K = 5

def safe_read_csv(path: Path):
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception as e:
        print(f"Failed to read {path}: {e}", file=sys.stderr)
        return None

def row_to_doc_from_alerts(idx, row):
    # build a concise text for alert rows
    # adapt to your CSV columns present
    timestamp = row.get("timestamp") or row.get("ts") or row.get("date") or ""
    typ = row.get("event_type") or row.get("type") or row.get("alert_type") or ""
    location = row.get("location") or row.get("stop_name") or row.get("stop") or ""
    details = []
    for c in ["message", "description", "details", "note"]:
        if c in row and pd.notna(row[c]):
            details.append(str(row[c]))
    details_str = " ".join(details) if details else ""
    text = f"ALERT [{timestamp}] Type: {typ}. Location: {location}. {details_str}"
    meta = {"source_row": int(idx)}
    # try to include route/stop info if present
    for k in ["route_id", "route", "stop_id", "stop_code", "stop_name", "location"]:
        if k in row and pd.notna(row[k]):
            meta[k] = row[k]
    return {"source": ALERTS_F.name, "text": text.strip(), "meta": meta}

def row_to_doc_from_stops(idx, row):
    stop_id = row.get("stop_id") or row.get("stop_code") or ""
    name = row.get("stop_name") or row.get("name") or ""
    lat = row.get("stop_lat") or row.get("lat") or ""
    lon = row.get("stop_lon") or row.get("lon") or ""
    routes = row.get("routes") or row.get("route_ids") or ""
    text = f"STOP: {name} (id: {stop_id}). Coordinates: {lat}, {lon}."
    if pd.notna(routes) and str(routes).strip():
        text += f" Routes: {routes}."
    meta = {"source_row": int(idx), "stop_id": stop_id, "name": name}
    return {"source": STOPS_F.name, "text": text.strip(), "meta": meta}

def generic_row_to_doc(idx, row, source_name):
    # fallback: stringify row but keep concise
    snippet = []
    for col in row.index:
        val = row.get(col)
        if pd.isna(val): continue
        s = str(val)
        if len(s) > 250:
            s = s[:250] + "..."
        snippet.append(f"{col}: {s}")
    text = f"{source_name} ROW {idx} — " + " | ".join(snippet)
    return {"source": source_name, "text": text, "meta": {"source_row": int(idx)}}

def chunk_text(text, chunk_words=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
    words = text.split()
    if len(words) <= chunk_words:
        return [text]
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_words]
        chunks.append(" ".join(chunk))
        i += chunk_words - overlap
    return chunks

def ingest():
    docs = []

    # Alerts
    df_alerts = safe_read_csv(ALERTS_F)
    if df_alerts is not None:
        print(f"Loading alerts: {len(df_alerts)} rows")
        for idx, row in df_alerts.iterrows():
            try:
                doc = row_to_doc_from_alerts(idx, row)
                docs.append(doc)
            except Exception as e:
                # fallback
                docs.append(generic_row_to_doc(idx, row, ALERTS_F.name))
    else:
        print("No alerts file found or failed to read.")

    # Stops
    df_stops = safe_read_csv(STOPS_F)
    if df_stops is not None:
        print(f"Loading stops: {len(df_stops)} rows")
        for idx, row in df_stops.iterrows():
            try:
                doc = row_to_doc_from_stops(idx, row)
                docs.append(doc)
            except Exception as e:
                docs.append(generic_row_to_doc(idx, row, STOPS_F.name))
    else:
        print("No stops file found or failed to read.")

    # Optional extras
    for f in EXTRA_FILES:
        df = safe_read_csv(f)
        if df is None:
            continue
        print(f"Loading extra {f.name}: {len(df)} rows")
        for idx, row in df.iterrows():
            try:
                docs.append(generic_row_to_doc(idx, row, f.name))
            except Exception:
                docs.append(generic_row_to_doc(idx, row, f.name))

    print(f"Total base docs: {len(docs)}")

    # Expand / chunk
    expanded = []
    for i, d in enumerate(docs):
        chunks = chunk_text(d["text"])
        for ci, c in enumerate(chunks):
            expanded.append({
                "source": d["source"],
                "text": c,
                "meta": d.get("meta", {}),
                "chunk_id": ci,
                "orig_idx": i
            })

    print(f"Total chunks after chunking: {len(expanded)}")

    # Load embedding model
    print("Loading embedding model:", EMBED_MODEL)
    model = SentenceTransformer(EMBED_MODEL)

    texts = [e["text"] for e in expanded]
    print("Encoding embeddings (this may take a moment)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    # normalize for cosine similarity using inner product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    dim = embeddings.shape[1]
    print(f"Embedding dimension: {dim}")

    # build faiss index (IndexFlatIP for cosine with normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    faiss.write_index(index, str(OUT_DIR / "faiss_index.bin"))
    print("Saved faiss index to", OUT_DIR / "faiss_index.bin")

    # Save metadata aligned with index order
    meta = []
    for e in expanded:
        meta.append({
            "source": e["source"],
            "text": e["text"],
            "meta": e.get("meta", {}),
            "chunk_id": e["chunk_id"],
            "orig_idx": e["orig_idx"]
        })
    with open(OUT_DIR / "index_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("Saved metadata to", OUT_DIR / "index_meta.json")

    # small manifest
    manifest = {
        "num_docs": len(docs),
        "num_chunks": len(expanded),
        "embedding_model": EMBED_MODEL,
        "index_type": "faiss.IndexFlatIP",
    }
    with open(OUT_DIR / "sources.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("Saved manifest to", OUT_DIR / "sources.json")

    print("Ingest complete.")

if __name__ == "__main__":
    ingest()
