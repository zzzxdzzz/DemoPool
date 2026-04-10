"""
ingest.py  —  Document ingestion & vector database builder (memory-efficient)
=============================================================================
Supports:
  .md   — Mathpix-exported markdown (preferred: clean, equations preserved)
  .txt  — Plain text
  .pdf  — Raw PDF (fallback; use Mathpix for better quality)

Recommended workflow:
  1. Export PDFs from Mathpix Snipping Tool as Markdown → save to ./docs/raw/
  2. python scripts/preprocess.py   (clean the markdown)
  3. python scripts/ingest.py       (embed and index)

Usage:
    python scripts/ingest.py
    python scripts/ingest.py --docs-path /path/to/papers
    python scripts/ingest.py --reset          # clears DB and rebuilds
    python scripts/ingest.py --batch-size 25  # fewer chunks per batch (less RAM)
"""

import os
import sys
import gc
import argparse
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, MofNCompleteColumn, TimeElapsedColumn,
)

console = Console()

# ── Config ─────────────────────────────────────────────────────────────────
DOCS_PATH     = Path(os.getenv("DOCS_PATH", "./docs"))
CHROMA_PATH   = Path(os.getenv("CHROMA_DB_PATH", "./rag/vectordb"))
EMBED_MODEL   = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", 512))   # reduced from 1024
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 64)) # reduced from 128
COLLECTION    = "science_papers"
BATCH_SIZE    = 8    # chunks per batch — small to avoid MPS/OOM on Apple Silicon


# ── Text extraction ────────────────────────────────────────────────────────
def extract_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz), fallback to pypdf."""
    try:
        import fitz
        doc = fitz.open(str(path))
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        console.log(f"[yellow]  Skipping {path.name}: {e}[/]")
        return ""


def extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_md(path: Path) -> str:
    """
    Read a Mathpix markdown file.
    Strips markdown syntax characters that add noise without semantic value
    (heading hashes, bold/italic markers, horizontal rules) while preserving
    LaTeX math inline and block expressions, which carry scientific meaning.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")

    # Keep LaTeX math but protect it from stripping (placeholder swap)
    # Block math: $$...$$
    block_math, inline_math = [], []
    def save_block(m):
        block_math.append(m.group(0))
        return f"__BLOCKMATH{len(block_math)-1}__"
    def save_inline(m):
        inline_math.append(m.group(0))
        return f"__INLINEMATH{len(inline_math)-1}__"

    import re
    text = re.sub(r"\$\$[\s\S]*?\$\$", save_block, text)
    text = re.sub(r"\$[^$\n]+?\$", save_inline, text)

    # Strip markdown syntax
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)        # bold/italic
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)          # underline
    text = re.sub(r"^[-*]{3,}\s*$", "", text, flags=re.MULTILINE)  # hr
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)                  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)         # links → text
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)        # blockquotes
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)               # code spans

    # Restore math
    for i, m in enumerate(inline_math):
        text = text.replace(f"__INLINEMATH{i}__", m)
    for i, m in enumerate(block_math):
        text = text.replace(f"__BLOCKMATH{i}__", m)

    return text


# ── Chunking ───────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split on words with overlap, skip short/empty chunks."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) > 80:
            chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks


# ── Embedding model ────────────────────────────────────────────────────────
def load_embed_model():
    from sentence_transformers import SentenceTransformer
    console.log(f"Loading embedding model: [cyan]{EMBED_MODEL}[/]")
    console.log("  [dim](first run downloads ~130 MB, then cached)[/]")
    # Force CPU — avoids MPS (Apple Metal) OOM kills on unified memory Macs.
    # BGE-small is 130 MB; CPU inference is fast enough and stable.
    model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return model


# ── ChromaDB ───────────────────────────────────────────────────────────────
def get_collection(reset: bool = False):
    import chromadb
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if reset:
        try:
            client.delete_collection(COLLECTION)
            console.log("[yellow]Cleared existing vector database.[/]")
        except Exception:
            pass
    col = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return col


# ── Main ingestion ─────────────────────────────────────────────────────────
def ingest(docs_path: Path, reset: bool, batch_size: int):
    if not docs_path.exists():
        console.print(f"[red]Docs folder not found: {docs_path}[/]")
        sys.exit(1)

    # Prefer .md (Mathpix) > .txt > .pdf  — collect all three
    md_files  = sorted(docs_path.rglob("*.md"),
                       key=lambda p: p.name.lower())
    txt_files = sorted(docs_path.rglob("*.txt"),
                       key=lambda p: p.name.lower())
    pdf_files = sorted(docs_path.rglob("*.pdf"),
                       key=lambda p: p.name.lower())

    # Skip .md files inside docs/raw/ — those are the uncleaned originals
    raw_dir   = docs_path / "raw"
    md_files  = [f for f in md_files if not f.is_relative_to(raw_dir)]

    all_files = md_files + txt_files + pdf_files
    if not all_files:
        console.print(Panel(
            "[yellow]No PDF or TXT files found in ./docs[/]\n"
            "Add your science papers there and run again.",
            border_style="yellow"
        ))
        sys.exit(0)

    console.print(Panel(
        f"[bold cyan]Science LLM — Document Ingestion[/]\n"
        f"Markdown (.md): [bold]{len(md_files)}[/]  "
        f"Text (.txt): [bold]{len(txt_files)}[/]  "
        f"PDF (.pdf): [bold]{len(pdf_files)}[/]\n"
        f"Docs path : [dim]{docs_path}[/]\n"
        f"Vector DB : [dim]{CHROMA_PATH}[/]\n"
        f"Chunk sz  : [dim]{CHUNK_SIZE} words, overlap {CHUNK_OVERLAP}[/]\n"
        f"Batch sz  : [dim]{batch_size} chunks per batch[/]",
        border_style="cyan"
    ))

    # Load models once
    embed_model = load_embed_model()
    collection  = get_collection(reset=reset)

    # Pre-check already-indexed file names to allow incremental updates
    existing_meta = collection.get(include=["metadatas"])
    already_indexed = {
        m.get("file_name", "") for m in (existing_meta.get("metadatas") or [])
    }
    if already_indexed:
        console.log(f"[dim]{len(already_indexed)} file(s) already in DB — skipping them[/]")

    total_chunks_added = 0
    doc_id_counter = collection.count()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        file_task = progress.add_task("Processing files", total=len(all_files))

        for fpath in all_files:
            progress.update(file_task, description=f"[cyan]{fpath.name[:40]}[/]")

            # Skip already-indexed files (incremental mode)
            if fpath.name in already_indexed and not reset:
                console.log(f"  [dim]Skip (already indexed): {fpath.name}[/]")
                progress.advance(file_task)
                continue

            # Extract text — dispatch by file type
            suffix = fpath.suffix.lower()
            if suffix == ".md":
                text = extract_md(fpath)
            elif suffix == ".pdf":
                text = extract_pdf(fpath)
            else:
                text = extract_txt(fpath)

            if not text.strip():
                console.log(f"  [yellow]Empty/unreadable: {fpath.name}[/]")
                progress.advance(file_task)
                continue

            # Chunk
            chunks = chunk_text(text)
            if not chunks:
                progress.advance(file_task)
                continue

            console.log(
                f"  [green]{fpath.name}[/]: "
                f"{len(chunks)} chunks → embedding in batches of {batch_size}"
            )

            # Embed and store in batches
            chunk_task = progress.add_task(
                f"  Embedding", total=len(chunks)
            )

            for i in range(0, len(chunks), batch_size):
                batch_texts = chunks[i : i + batch_size]

                # Embed — encode one-by-one inside the batch to cap peak RAM
                embeddings = embed_model.encode(
                    batch_texts,
                    batch_size=4,            # sentence_transformers inner batch
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                ).tolist()

                # Prepare ChromaDB records
                ids  = [f"doc_{doc_id_counter + j}" for j in range(len(batch_texts))]
                metas = [
                    {
                        "file_name": fpath.name,
                        "file_path": str(fpath),
                        "chunk_index": i + j,
                        "total_chunks": len(chunks),
                    }
                    for j in range(len(batch_texts))
                ]

                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=batch_texts,
                    metadatas=metas,
                )

                doc_id_counter   += len(batch_texts)
                total_chunks_added += len(batch_texts)
                progress.advance(chunk_task, len(batch_texts))

                # Free memory between batches
                del embeddings, batch_texts
                gc.collect()

            progress.remove_task(chunk_task)
            progress.advance(file_task)

    console.print(Panel(
        f"[bold green]Ingestion complete![/]\n\n"
        f"  New chunks added  : [bold]{total_chunks_added}[/]\n"
        f"  Total in DB       : [bold]{collection.count()}[/]\n"
        f"  Vector DB path    : [dim]{CHROMA_PATH}[/]\n\n"
        "[dim]Run [bold]python scripts/chat.py[/] to start chatting.",
        title="Done ✓",
        border_style="green"
    ))


def main():
    parser = argparse.ArgumentParser(description="Ingest PDFs into the vector database")
    parser.add_argument("--docs-path",  type=Path, default=DOCS_PATH)
    parser.add_argument("--reset",      action="store_true",
                        help="Clear the DB before ingesting")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help="Chunks per batch (lower = less RAM, default 32)")
    args = parser.parse_args()
    ingest(args.docs_path, args.reset, args.batch_size)


if __name__ == "__main__":
    main()
