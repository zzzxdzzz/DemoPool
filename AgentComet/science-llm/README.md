# Science LLM — Local AI Research Assistant

A fully local AI system for scientists, built on **Mistral 7B Instruct v0.3**, optimized for Apple Silicon. No API keys, no cloud, no data leaving your machine.

---

## Why Mistral 7B?

| | Mistral 7B | Phi-3.5 Mini | Qwen2.5 7B | Gemma 2 9B |
|---|---|---|---|---|
| Scientific reasoning | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Apple Silicon (MLX) | ✅ Native | ✅ Good | ✅ Good | ⚠️ Limited |
| LoRA fine-tuning | ✅ Full | ⚠️ Partial | ✅ Full | ⚠️ Limited |
| Context window | 32k | 128k | 128k | 8k |
| VRAM (4-bit) | ~4.1 GB | ~2.5 GB | ~4.1 GB | ~5.5 GB |

Mistral 7B has the best balance of scientific capability, MLX support, and fine-tuning compatibility.

---

## Architecture

```
./docs/               ← Drop your PDFs & books here
    paper1.pdf
    textbook.pdf
    ...

scripts/
    ingest.py         ← Step 1: Index your documents
    chat.py           ← Step 2: Chat with your library (RAG)
    prepare_finetune.py ← Step 3: Build training dataset
    finetune.py       ← Step 4: Fine-tune the model (LoRA)
    export_ollama.py  ← Step 5: Deploy fine-tuned model

rag/
    vectordb/         ← ChromaDB (auto-created by ingest.py)

finetune/
    data/             ← Training JSONL files (auto-created)

models/
    lora-adapters/    ← LoRA weights (auto-created by finetune.py)
    fused-model/      ← Merged model (auto-created by --fuse)
```

**RAG stack**: LlamaIndex → ChromaDB → BGE embeddings → Mistral 7B via Ollama
**Fine-tuning stack**: MLX-LM + LoRA on Apple Silicon Metal GPU

---

## Quick Start

### 1. Install everything

```bash
chmod +x setup.sh
./setup.sh
```

This installs:
- **Ollama** (runs Mistral 7B locally via Apple Metal)
- **mlx-lm** (Apple's fine-tuning framework)
- **LlamaIndex + ChromaDB** (RAG pipeline)
- **BGE-small embeddings** (local, ~130MB)

### 2. Add your documents

```bash
# Copy your PDFs and books to the docs folder
cp ~/Downloads/your-paper.pdf ./docs/
cp ~/Books/science-textbook.pdf ./docs/
# (supports nested folders too)
```

### 3. Index your library

```bash
source .venv/bin/activate
python scripts/ingest.py
```

Output:
```
Found 3 PDF(s)
Loaded 847 document pages
Embedding and indexing documents... ✓
Total chunks in DB: 1,203
```

### 4. Start chatting

```bash
python scripts/chat.py
```

```
You: What methods are used to measure cometary nucleus composition?
Assistant: Based on your library, several methods are described...
  Sources: → spectroscopy-review.pdf, p.14 (relevance: 0.91)
```

---

## Fine-tuning Your Model (Optional but Powerful)

Fine-tuning teaches Mistral the specific vocabulary, citation style, and reasoning patterns from YOUR documents. RAG retrieves context at query time; fine-tuning bakes knowledge into the model weights.

### Step 1: Prepare training data

```bash
python scripts/prepare_finetune.py --num-pairs 500
```

This generates `finetune/data/train.jsonl`, `valid.jsonl`, `test.jsonl` from your PDFs.

### Step 2: Fine-tune with LoRA

```bash
# Standard (16GB RAM Mac — recommended)
python scripts/finetune.py --iters 1000

# Light (8GB RAM Mac)
python scripts/finetune.py --iters 500 --batch-size 1 --lora-rank 8

# Extended (for large document collections)
python scripts/finetune.py --iters 2000
```

Training time on Apple Silicon:
- M1 Pro (16GB): ~2-3 hours for 1000 iterations
- M2 Max (32GB): ~45-60 min for 1000 iterations
- M3 Ultra (192GB): ~15-20 min for 1000 iterations

### Step 3: Test the fine-tuned model

```bash
python scripts/finetune.py --test
```

### Step 4: Fuse and deploy

```bash
# Merge LoRA adapters into base model
python scripts/finetune.py --fuse

# Register with Ollama
python scripts/export_ollama.py --model-name science-mistral
```

---

## Chat Commands

While in `python scripts/chat.py`:

| Command | Description |
|---|---|
| `/summarize <topic>` | Summarize a topic from your library |
| `/sources` | List all indexed documents |
| `/top <N>` | Change retrieval depth (default: 5) |
| `/clear` | Clear the screen |
| `/quit` | Exit |

---

## Adding New Documents

Whenever you add new PDFs to `./docs/`:

```bash
# Add new files only (incremental)
python scripts/ingest.py

# Rebuild from scratch (if you removed old files too)
python scripts/ingest.py --reset
```

---

## Configuration

Edit `.env` to customize behavior:

```bash
MODEL_NAME=mistral:7b-instruct-v0.3-q4_K_M  # Ollama model name
CHUNK_SIZE=1024          # Characters per chunk (larger = more context, slower)
CHUNK_OVERLAP=128        # Overlap between chunks
TOP_K_RETRIEVAL=5        # Chunks retrieved per query (increase for complex Qs)
EMBED_MODEL=BAAI/bge-small-en-v1.5  # Local embedding model
```

---

## Hardware Requirements

| Task | Minimum RAM | Recommended |
|---|---|---|
| RAG (chat.py) | 8 GB | 16 GB |
| Fine-tuning (batch=1) | 8 GB | 16 GB |
| Fine-tuning (batch=2) | 16 GB | 32 GB |
| Fine-tuning (batch=4) | 32 GB | 64 GB |

---

## Troubleshooting

**"Cannot connect to Ollama"**
```bash
# Start Ollama service
ollama serve
# In another terminal:
python scripts/chat.py
```

**"Out of memory during fine-tuning"**
```bash
python scripts/finetune.py --batch-size 1 --lora-rank 8
```

**"No documents found"**
- Make sure PDFs are in `./docs/` (not subfolders named differently)
- Run `python scripts/ingest.py --reset` to rebuild the index

**Slow embeddings on first run**
- The BGE-small model (~130MB) downloads once and caches locally
- Subsequent runs are fast

---

## Full Workflow Summary

```
1. ./setup.sh                          # install everything
2. cp papers/*.pdf ./docs/             # add your library
3. python scripts/ingest.py            # build vector DB
4. python scripts/chat.py              # start chatting (RAG)

# Optional fine-tuning:
5. python scripts/prepare_finetune.py  # create training data
6. python scripts/finetune.py          # train LoRA on Apple Silicon
7. python scripts/finetune.py --fuse   # merge adapters
8. python scripts/export_ollama.py     # deploy to Ollama
9. python scripts/chat.py              # chat with fine-tuned model
```
