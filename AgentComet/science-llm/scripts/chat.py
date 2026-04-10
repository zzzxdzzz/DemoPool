"""
chat.py  —  Interactive science paper Q&A interface
=====================================================
Chat with your ingested science library using RAG.
Retrieves relevant chunks directly from ChromaDB (no LlamaIndex overhead),
then sends them to Mistral 7B running locally via Ollama.

Usage:
    python scripts/chat.py
    python scripts/chat.py --top-k 8   # retrieve more context
    python scripts/chat.py --query "What is cometary outgassing?"  # single query
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

console = Console()

# ── Config ─────────────────────────────────────────────────────────────────
CHROMA_PATH = Path(os.getenv("CHROMA_DB_PATH", "./rag/vectordb"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
MODEL_NAME  = os.getenv("MODEL_NAME", "mistral:7b-instruct-v0.3-q4_K_M")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
TOP_K       = int(os.getenv("TOP_K_RETRIEVAL", 5))
COLLECTION  = "science_papers"

SYSTEM_PROMPT = """\
You are an expert scientific research assistant. Answer questions using ONLY \
the provided context excerpts from the user's personal science library.

Rules:
- Cite sources as [filename, chunk N] when referencing specific content.
- If the answer is not in the context, say: "I don't have information on this \
  in your current library."
- Use precise scientific language.
- For complex questions, reason step by step.
"""


# ── Load models (once at startup) ─────────────────────────────────────────
def load_resources():
    """Load embedding model and connect to ChromaDB."""
    # Check DB exists
    if not CHROMA_PATH.exists() or not any(CHROMA_PATH.iterdir()):
        console.print(Panel(
            "[yellow]No indexed documents found.[/]\n\n"
            "Run first:\n  [bold]python scripts/ingest.py[/]",
            title="Vector DB empty", border_style="yellow"
        ))
        sys.exit(1)

    # Embedding model
    with console.status(f"Loading embedding model [cyan]{EMBED_MODEL}[/]..."):
        from sentence_transformers import SentenceTransformer
        embed_model = SentenceTransformer(EMBED_MODEL, device="cpu")

    # ChromaDB
    import chromadb
    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION)
    total      = collection.count()

    if total == 0:
        console.print("[yellow]Vector DB is empty. Run ingest.py first.[/]")
        sys.exit(1)

    console.log(f"Vector DB: [bold green]{total}[/] chunks ready")
    return embed_model, collection


# ── Retrieval ──────────────────────────────────────────────────────────────
def retrieve(query: str, embed_model, collection, top_k: int) -> List[Dict]:
    """Embed the query and find the most relevant chunks."""
    q_vec = embed_model.encode(
        [query], normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=q_vec,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":     doc,
            "file":     meta.get("file_name", "unknown"),
            "chunk":    meta.get("chunk_index", "?"),
            "score":    round(1 - dist, 3),  # cosine similarity
        })
    return chunks


# ── Ollama call ────────────────────────────────────────────────────────────
def ask_ollama(question: str, context_chunks: List[Dict]) -> str:
    """Build a RAG prompt and call Mistral via Ollama's REST API."""
    import urllib.request

    # Build context block
    context_text = "\n\n---\n\n".join(
        f"[{c['file']}, chunk {c['chunk']}] (relevance {c['score']}):\n{c['text']}"
        for c in context_chunks
    )

    user_message = (
        f"Context from the science library:\n\n"
        f"{context_text}\n\n"
        f"---\n\n"
        f"Question: {question}"
    )

    payload = json.dumps({
        "model":  MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": user_message,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "top_p":       0.9,
            "num_ctx":     4096,
        },
    }).encode()

    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        full_response = ""
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode().strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    full_response += token
                    print(token, end="", flush=True)
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
        print()  # newline after streaming
        return full_response

    except ConnectionRefusedError:
        console.print(Panel(
            "[red]Cannot connect to Ollama.[/]\n\n"
            "Start it with:\n  [bold]brew services start ollama[/]",
            title="Ollama not running", border_style="red"
        ))
        return ""
    except Exception as e:
        console.print(f"[red]Ollama error: {e}[/]")
        return ""


# ── Chat loop ──────────────────────────────────────────────────────────────
def print_header(total_chunks: int):
    console.print(Panel(
        f"[bold cyan]Science LLM — Research Assistant[/]\n"
        f"Model: [dim]{MODEL_NAME}[/]  |  "
        f"DB: [dim]{total_chunks} chunks[/]  |  "
        f"Top-K: [dim]{TOP_K}[/]\n\n"
        "Commands:\n"
        "  [bold]/summarize <topic>[/]  summarize a topic from your library\n"
        "  [bold]/sources[/]            list all indexed documents\n"
        "  [bold]/top <N>[/]            change retrieval depth\n"
        "  [bold]/quit[/]               exit",
        border_style="cyan"
    ))


def show_sources(collection):
    results = collection.get(include=["metadatas"])
    files = sorted({
        m.get("file_name", "?")
        for m in (results.get("metadatas") or [])
        if m
    })
    console.print(Panel(
        "\n".join(f"  [cyan]·[/] {f}" for f in files),
        title=f"Indexed Documents ({len(files)} files)",
        border_style="cyan"
    ))


def chat_loop(embed_model, collection, top_k: int):
    print_header(collection.count())
    console.print("[dim]Ask any question about your science library.\n[/]")
    current_top_k = top_k

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "exit", "quit"):
            console.print("[dim]Goodbye![/]")
            break
        if user_input.lower() == "/clear":
            console.clear()
            print_header(collection.count())
            continue
        if user_input.lower() == "/sources":
            show_sources(collection)
            continue
        if user_input.lower().startswith("/top "):
            try:
                current_top_k = int(user_input.split()[1])
                console.print(f"[dim]Retrieval depth → {current_top_k}[/]")
            except (ValueError, IndexError):
                console.print("[red]Usage: /top <number>[/]")
            continue
        if user_input.lower().startswith("/summarize "):
            topic = user_input[11:].strip()
            user_input = (
                f"Provide a comprehensive scientific summary of: {topic}\n"
                "Include: main research question, methodology, key findings, "
                "conclusions, limitations, and key concepts."
            )

        # ── Retrieve + Answer ──────────────────────────────────────────
        with console.status("Retrieving relevant passages..."):
            chunks = retrieve(user_input, embed_model, collection, current_top_k)

        if not chunks:
            console.print("[yellow]No relevant passages found.[/]")
            continue

        console.print(
            f"[dim]Retrieved {len(chunks)} passages "
            f"(top relevance: {chunks[0]['score']})[/]\n"
        )
        console.print("[bold magenta]Assistant[/] ", end="")

        ask_ollama(user_input, chunks)

        # Show sources
        console.print()
        seen = set()
        for c in chunks:
            key = c["file"]
            if key not in seen:
                seen.add(key)
                console.print(
                    f"  [dim]→ {c['file']}, chunk {c['chunk']} "
                    f"(relevance {c['score']})[/]"
                )
        console.print()


def main():
    parser = argparse.ArgumentParser(description="Chat with your science library")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--query", type=str, default=None,
                        help="Single non-interactive query")
    args = parser.parse_args()

    embed_model, collection = load_resources()

    if args.query:
        chunks = retrieve(args.query, embed_model, collection, args.top_k)
        ask_ollama(args.query, chunks)
        for c in chunks:
            console.print(f"  [dim]→ {c['file']}, chunk {c['chunk']} ({c['score']})[/]")
    else:
        chat_loop(embed_model, collection, args.top_k)


if __name__ == "__main__":
    main()
