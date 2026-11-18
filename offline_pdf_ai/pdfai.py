"""
pdfai.py - Ask questions about a folder of PDFs, completely offline.

Setup (once):
    1. Install Ollama            https://ollama.com
    2. ollama pull nomic-embed-text
       ollama pull llama3.2:3b
    3. pip install pypdfium2 numpy requests pillow

Use:
    python pdfai.py index  my_pdfs
    python pdfai.py ask    "What is the minimum stair width?"  --show
    python pdfai.py chat
"""
import argparse, json, os, sys, time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import requests
from PIL import ImageDraw

# ---------------- settings ----------------
OLLAMA      = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL  = "llama3.2:3b"
INDEX_DIR   = Path("index")
CHUNK_SIZE  = 900     # characters per passage
OVERLAP     = 150     # characters shared by neighbouring passages
TOP_K       = 4       # passages given to the model
MIN_SCORE   = 0.55    # below this similarity we say "not found"
NOT_FOUND   = "I couldn't find that in your documents."


# ---------------- 1. talk to the local models ----------------
def embed(texts, kind):
    """Turn texts into unit-length vectors. kind: search_document | search_query"""
    r = requests.post(f"{OLLAMA}/api/embed", json={
        "model": EMBED_MODEL,
        "input": [f"{kind}: {t}" for t in texts]})
    r.raise_for_status()
    v = np.array(r.json()["embeddings"], dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def generate(messages):
    """Stream the local LLM's reply to the screen, return the full text."""
    reply = ""
    with requests.post(f"{OLLAMA}/api/chat", stream=True, json={
            "model": CHAT_MODEL, "messages": messages,
            "options": {"temperature": 0, "num_ctx": 4096}}) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                piece = json.loads(line).get("message", {}).get("content", "")
                print(piece, end="", flush=True)
                reply += piece
    return reply


# ---------------- 2. PDFs -> pages -> passages ----------------
def read_pages(folder):
    """Yield (file, page_number, text) for every page of every PDF."""
    for path in sorted(Path(folder).rglob("*.pdf")):
        pdf = pdfium.PdfDocument(path)
        for i, page in enumerate(pdf):
            yield path.resolve(), i + 1, page.get_textpage().get_text_range()
        pdf.close()


def chunk(text):
    """Split one page into overlapping windows. Yields (start, end) offsets."""
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):                         # prefer to cut at a sentence
            cut = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            if cut > start + CHUNK_SIZE // 2:
                end = cut + 1
        yield start, end
        if end == len(text):
            break
        start = end - OVERLAP


# ---------------- 3. build the index ----------------
def build_index(folder):
    chunks = []
    for path, page_no, text in read_pages(folder):
        for s, e in chunk(text):
            clean = " ".join(text[s:e].split())
            if len(clean) > 40:                     # skip headers, page numbers
                chunks.append({"file": str(path), "page": page_no,
                               "start": s, "end": e, "text": clean})
    if not chunks:
        sys.exit("No text found. Scanned PDFs need OCR first.")

    vectors = []
    for i in range(0, len(chunks), 32):             # 32 passages per request
        batch = [c["text"] for c in chunks[i:i + 32]]
        vectors.append(embed(batch, "search_document"))
        print(f"  embedded {min(i + 32, len(chunks))}/{len(chunks)}", end="\r")

    INDEX_DIR.mkdir(exist_ok=True)
    np.save(INDEX_DIR / "vectors.npy", np.vstack(vectors))
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
    print(f"\nIndexed {len(chunks)} passages from {folder}")


# ---------------- 4. search ----------------
@lru_cache(maxsize=1)
def load_index():
    vectors = np.load(INDEX_DIR / "vectors.npy")
    chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    return vectors, chunks


def search(question, k=TOP_K):
    vectors, chunks = load_index()
    q = embed([question], "search_query")[0]
    scores = vectors @ q                            # cosine similarity
    best = np.argsort(-scores)[:k]
    return [(float(scores[i]), chunks[i]) for i in best]


# ---------------- 5. answer with citations ----------------
SYSTEM = f"""You answer questions using ONLY the numbered sources below.
Cite the source number after every fact, like [1] or [2].
If the sources do not contain the answer, reply exactly:
{NOT_FOUND}"""


def ask(question):
    t0 = time.time()
    hits = search(question)
    best = hits[0][0]
    hits = [h for h in hits if h[0] >= MIN_SCORE]   # guard 1: relevance
    t1 = time.time()
    if not hits:
        print(f"{NOT_FOUND}  (best match only {best:.2f})")
        return []

    sources = "\n\n".join(
        f"[{n}] {Path(c['file']).name}, page {c['page']}:\n{c['text']}"
        for n, (_, c) in enumerate(hits, 1))
    reply = generate([                              # guard 2: the prompt rule
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Sources:\n{sources}\n\nQuestion: {question}"}])
    t2 = time.time()

    if NOT_FOUND not in reply:
        print("\n\nSources:")
        for n, (score, c) in enumerate(hits, 1):
            print(f"  [{n}] {Path(c['file']).name}  page {c['page']}  (match {score:.2f})")
    print(f"\nTime: search {t1 - t0:.1f}s | answer {t2 - t1:.1f}s")
    return hits


# ---------------- 6. prove it: show the page ----------------
def show(c, out="source.png", scale=2):
    """Render the cited page and highlight the exact passage in yellow."""
    pdf = pdfium.PdfDocument(c["file"])
    page = pdf[c["page"] - 1]
    img = page.render(scale=scale).to_pil().convert("RGB")
    text_page, height = page.get_textpage(), page.get_height()
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(text_page.count_rects(c["start"], c["end"] - c["start"])):
        left, bottom, right, top = text_page.get_rect(i)
        draw.rectangle([left * scale, (height - top) * scale,
                        right * scale, (height - bottom) * scale],
                       fill=(255, 220, 0, 90))
    img.save(out)
    pdf.close()
    print(f"Opened {Path(c['file']).name}, page {c['page']} -> {out}")
    if sys.platform == "win32":
        os.startfile(out)


# ---------------- 7. command line ----------------
def chat():
    hits = []
    print("Ask anything. 'show 1' opens source [1]. 'quit' to exit.")
    while True:
        q = input("\nYou> ").strip()
        if q.lower() in ("", "quit", "exit"):
            break
        if q.startswith("show ") and hits:
            show(hits[int(q.split()[1]) - 1][1])
        else:
            hits = ask(q)


def main():
    p = argparse.ArgumentParser(description="Offline PDF question answering")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index").add_argument("folder")
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--show", action="store_true", help="open the top source page")
    sub.add_parser("chat")
    args = p.parse_args()

    if args.cmd == "index":
        build_index(args.folder)
    elif args.cmd == "ask":
        hits = ask(args.question)
        if args.show and hits:
            show(hits[0][1])
    else:
        chat()


if __name__ == "__main__":
    main()
