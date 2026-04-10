#!/bin/bash
# =============================================================================
# Science LLM - Local Setup Script for Apple Silicon
# Model: Mistral 7B Instruct v0.3
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║        Science LLM - Local Setup (Apple Silicon)     ║"
echo "║        Model: Mistral 7B Instruct v0.3               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Check Apple Silicon ─────────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Checking system...${NC}"
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo -e "${RED}Warning: This script is optimized for Apple Silicon (arm64). Found: $ARCH${NC}"
fi
echo "  Architecture: $ARCH ✓"
echo "  macOS: $(sw_vers -productVersion) ✓"

# ── 2. Install Homebrew if missing ─────────────────────────────────────────
echo -e "${YELLOW}[2/6] Checking Homebrew...${NC}"
if ! command -v brew &>/dev/null; then
    echo "  Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "  Homebrew already installed ✓"
fi

# ── 3. Install Ollama ──────────────────────────────────────────────────────
echo -e "${YELLOW}[3/6] Installing Ollama...${NC}"
if ! command -v ollama &>/dev/null; then
    echo "  Installing Ollama via Homebrew..."
    brew install ollama
    echo "  Ollama installed ✓"
else
    echo "  Ollama already installed ✓"
fi

# Start Ollama server if not already running
if ! ollama list &>/dev/null 2>&1; then
    echo "  Starting Ollama server..."
    brew services start ollama
    echo "  Waiting for Ollama to be ready..."
    for i in $(seq 1 15); do
        if ollama list &>/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

# Pull Mistral 7B model
echo "  Pulling mistral:7b-instruct-v0.3-q4_K_M (quantized for Apple Silicon)..."
echo "  This may take a few minutes (~4.1 GB download)..."
ollama pull mistral:7b-instruct-v0.3-q4_K_M
echo "  Model ready ✓"

# ── 4. Python environment ──────────────────────────────────────────────────
echo -e "${YELLOW}[4/6] Setting up Python environment...${NC}"

if ! command -v python3 &>/dev/null; then
    echo "  Installing Python 3..."
    brew install python@3.11
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "  Python $PYTHON_VERSION ✓"

# Create virtual environment
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  Virtual environment created ✓"
else
    echo "  Virtual environment exists ✓"
fi

source .venv/bin/activate

# ── 5. Install Python dependencies ────────────────────────────────────────
echo -e "${YELLOW}[5/6] Installing Python packages...${NC}"

pip install --upgrade pip --quiet

echo "  Installing RAG dependencies..."
pip install --quiet \
    llama-index \
    llama-index-vector-stores-chroma \
    llama-index-embeddings-huggingface \
    llama-index-llms-ollama \
    chromadb \
    pypdf \
    pymupdf \
    sentence-transformers \
    rich \
    click \
    python-dotenv

echo "  Installing MLX fine-tuning dependencies..."
pip install --quiet \
    mlx-lm \
    datasets \
    huggingface_hub \
    transformers \
    accelerate

echo "  All packages installed ✓"

# ── 6. Create .env config ─────────────────────────────────────────────────
echo -e "${YELLOW}[6/6] Creating configuration...${NC}"

if [ ! -f ".env" ]; then
cat > .env << 'EOF'
# Science LLM Configuration
MODEL_NAME=mistral:7b-instruct-v0.3-q4_K_M
MLX_MODEL=mistralai/Mistral-7B-Instruct-v0.3
OLLAMA_HOST=http://localhost:11434
CHROMA_DB_PATH=./rag/vectordb
DOCS_PATH=./docs
FINETUNE_DATA_PATH=./finetune/data
EMBED_MODEL=BAAI/bge-small-en-v1.5
CHUNK_SIZE=1024
CHUNK_OVERLAP=128
TOP_K_RETRIEVAL=5
EOF
    echo "  .env config created ✓"
else
    echo "  .env config exists ✓"
fi

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗"
echo "║                 Setup Complete! ✓                    ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Next steps:                                         ║"
echo "║  1. Add PDFs/books to the ./docs folder              ║"
echo "║  2. Run:  python scripts/ingest.py                   ║"
echo "║     (indexes your documents into the vector DB)      ║"
echo "║  3. Run:  python scripts/chat.py                     ║"
echo "║     (start chatting with your science library)       ║"
echo "║                                                      ║"
echo "║  For fine-tuning (after adding docs):                ║"
echo "║     python scripts/prepare_finetune.py               ║"
echo "║     python scripts/finetune.py                       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
