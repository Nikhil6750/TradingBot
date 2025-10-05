# knowledge/index_knowledge.py — STREAMING INDEXER v3 (hard caps, low RAM, clear logs)
import os, glob, time
import chromadb
from sentence_transformers import SentenceTransformer

DB_DIR = "rag_db"
COLLECTION_NAME = "knowledge_base"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

MIN_CHARS = 20
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
BATCH_SIZE = 4
MAX_FILE_BYTES = 1 * 1024 * 1024      # 1 MB per file guardrail
MAX_CHUNKS_PER_FILE = 50              # hard stop per file
MAX_TOTAL_CHUNKS = 500                # hard stop overall

def log(msg): print(time.strftime("[%H:%M:%S]"), msg, flush=True)

def file_size(path:str) -> int:
    try: return os.path.getsize(path)
    except: return 0

def too_big(path:str) -> bool:
    return file_size(path) > MAX_FILE_BYTES

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def chunk_stream(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Yield chunks without keeping them all in memory."""
    text = (text or "").strip()
    if not text: return
    n = len(text)
    if n <= size:
        yield text; return
    start = 0
    step = max(1, size - overlap)      # ensure progress even if overlap mis-set
    while start < n:
        end = min(n, start + size)
        yield text[start:end]
        start += step

def main():
    log("STREAMING INDEXER v3 — starting index build...")
    os.makedirs(DB_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_DIR)

    # Recreate collection to avoid 'where {}' issues and stale data
    try:
        client.delete_collection(COLLECTION_NAME)
        log("Old collection removed.")
    except Exception:
        pass
    coll = client.get_or_create_collection(COLLECTION_NAME)

    md_paths = sorted(glob.glob(os.path.join("knowledge", "*.md")))
    if not md_paths:
        log("No files under knowledge/*.md — nothing to index."); return

    # Show file list & sizes
    for p in md_paths:
        log(f"Found: {os.path.basename(p)} ({file_size(p)} bytes)")

    log(f"Loading embedder: {MODEL} (first run may download ~90MB)")
    embedder = SentenceTransformer(MODEL)

    total_files = 0
    total_chunks = 0

    for path in md_paths:
        name = os.path.basename(path)
        size_bytes = file_size(path)

        if too_big(path):
            log(f"!! Skipping {name}: > {MAX_FILE_BYTES//(1024*1024)}MB ({size_bytes} bytes).")
            continue

        try:
            text = read_text(path)
        except Exception as e:
            log(f"!! Could not read {name}: {e}")
            continue

        tlen = len((text or "").strip())
        if tlen < MIN_CHARS:
            log(f"- Skipping {name}: too few characters ({tlen})."); continue

        log(f"- {name}: {tlen} chars → chunking & indexing (streaming, max {MAX_CHUNKS_PER_FILE} chunks)…")

        ids_batch, docs_batch, metas_batch = [], [], []
        batch_idx = 0
        file_chunk_count = 0

        for i, ch in enumerate(chunk_stream(text)):
            # hard caps to prevent runaway
            if file_chunk_count >= MAX_CHUNKS_PER_FILE:
                log(f"  • Reached per-file cap ({MAX_CHUNKS_PER_FILE}) for {name}, skipping rest.")
                break
            if total_chunks >= MAX_TOTAL_CHUNKS:
                log(f"!! Reached global cap ({MAX_TOTAL_CHUNKS}) — stopping early.")
                break

            ids_batch.append(f"{name}:{i}")
            docs_batch.append(ch)
            metas_batch.append({"source": name})
            file_chunk_count += 1
            total_chunks += 1

            if len(docs_batch) >= BATCH_SIZE:
                vecs = embedder.encode(docs_batch, normalize_embeddings=True).tolist()
                coll.add(ids=ids_batch, embeddings=vecs, metadatas=metas_batch, documents=docs_batch)
                batch_idx += 1
                log(f"  • wrote batch {batch_idx} (+{len(docs_batch)} chunks)")
                ids_batch, docs_batch, metas_batch = [], [], []

        if docs_batch and total_chunks < MAX_TOTAL_CHUNKS:
            vecs = embedder.encode(docs_batch, normalize_embeddings=True).tolist()
            coll.add(ids=ids_batch, embeddings=vecs, metadatas=metas_batch, documents=docs_batch)
            batch_idx += 1
            log(f"  • wrote batch {batch_idx} (+{len(docs_batch)} chunks)")

        log(f"  = indexed {file_chunk_count} chunk(s) from {name}")
        total_files += 1

        if total_chunks >= MAX_TOTAL_CHUNKS:
            log(f"!! Global chunk cap hit ({MAX_TOTAL_CHUNKS}). Stopping.")
            break

    if total_chunks == 0:
        log("No content was indexed. Ensure your .md files have text.")
    else:
        log(f"Done. Indexed {total_chunks} chunk(s) from {total_files} file(s) into {DB_DIR}/ (collection={COLLECTION_NAME}).")

if __name__ == "__main__":
    main()
