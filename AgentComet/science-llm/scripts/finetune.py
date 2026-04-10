"""
finetune.py  —  Fine-tune Mistral 7B on your science library (Apple Silicon)
=============================================================================
Uses Apple's MLX-LM framework with LoRA (Low-Rank Adaptation) for
memory-efficient fine-tuning on Apple Silicon (M1/M2/M3/M4).

Requirements:
  - mlx-lm installed  (pip install mlx-lm)
  - Dataset prepared  (run prepare_finetune.py first)
  - ~16GB RAM recommended (8GB minimum with smaller batch size)

Usage:
    python scripts/finetune.py
    python scripts/finetune.py --iters 500    # quick training run
    python scripts/finetune.py --batch-size 1 # for 8GB RAM Macs
    python scripts/finetune.py --resume       # continue previous training

After fine-tuning, the LoRA adapters are saved to ./models/lora-adapters/
Run the fused model with:
    python scripts/finetune.py --fuse
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ── Config ─────────────────────────────────────────────────────────────────
MLX_MODEL        = os.getenv("MLX_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
FINETUNE_PATH    = Path(os.getenv("FINETUNE_DATA_PATH", "./finetune/data"))
ADAPTERS_PATH    = Path("./models/lora-adapters")
FUSED_PATH       = Path("./models/fused-model")


# ── LoRA hyperparameters (tuned for Apple Silicon) ─────────────────────────
LORA_CONFIG = {
    "model": str(MLX_MODEL),
    "train": True,
    "data": str(FINETUNE_PATH),
    "seed": 42,
    # LoRA settings
    "lora_layers": 16,       # number of transformer layers to apply LoRA to
    "lora_rank": 16,         # LoRA rank (higher = more capacity, more VRAM)
    "lora_scale": 20.0,      # LoRA scale factor
    "lora_dropout": 0.05,    # dropout for regularization
    # Training settings
    "batch_size": 2,         # reduce to 1 if OOM on 8GB Mac
    "iters": 1000,           # training iterations (~1-2 hours on M2)
    "val_batches": 25,
    "learning_rate": 1e-5,   # conservative LR for science text
    "steps_per_report": 10,
    "steps_per_eval": 100,
    "save_every": 200,
    "adapter_path": str(ADAPTERS_PATH),
    # Gradient checkpointing for memory efficiency
    "grad_checkpoint": True,
    # Optimizer
    "optimizer": "adam",
    "weight_decay": 0.01,
    "lr_schedule": "cosine_decay",
    "warmup_steps": 100,
}


def check_prerequisites():
    """Check that all required tools and data are present."""
    errors = []

    # Check mlx-lm
    result = subprocess.run(
        [sys.executable, "-c", "import mlx_lm; print('ok')"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        errors.append("mlx-lm not installed. Run: pip install mlx-lm")

    # Check dataset
    for split in ["train", "valid"]:
        fpath = FINETUNE_PATH / f"{split}.jsonl"
        if not fpath.exists():
            errors.append(f"Missing {fpath}. Run: python scripts/prepare_finetune.py")

    # Check dataset isn't empty
    train_path = FINETUNE_PATH / "train.jsonl"
    if train_path.exists():
        lines = train_path.read_text().strip().splitlines()
        if len(lines) < 10:
            errors.append(f"Training set too small ({len(lines)} samples). Add more documents.")

    if errors:
        console.print(Panel(
            "\n".join(f"[red]✗[/] {e}" for e in errors),
            title="Prerequisites not met",
            border_style="red"
        ))
        sys.exit(1)

    # Show dataset stats
    train_count = len((FINETUNE_PATH / "train.jsonl").read_text().strip().splitlines())
    valid_count = len((FINETUNE_PATH / "valid.jsonl").read_text().strip().splitlines())
    console.log(f"Dataset: [bold green]{train_count}[/] train / [bold]{valid_count}[/] valid")


def show_config(config: dict):
    """Display training configuration."""
    table = Table(title="Fine-tuning Configuration", border_style="cyan")
    table.add_column("Parameter", style="bold")
    table.add_column("Value", style="cyan")

    important_keys = [
        "model", "iters", "batch_size", "lora_rank", "lora_layers",
        "learning_rate", "adapter_path", "grad_checkpoint"
    ]
    for key in important_keys:
        if key in config:
            table.add_row(key, str(config[key]))

    console.print(table)


def run_training(config: dict):
    """Run MLX-LM fine-tuning."""
    ADAPTERS_PATH.mkdir(parents=True, exist_ok=True)

    # Save config to file for mlx-lm
    config_path = FINETUNE_PATH / "lora_config.yaml"
    import yaml
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(Panel(
        "[bold]Starting LoRA fine-tuning with MLX-LM[/]\n\n"
        f"Model       : [cyan]{config['model']}[/]\n"
        f"Iterations  : [cyan]{config['iters']}[/]\n"
        f"LoRA rank   : [cyan]{config['lora_rank']}[/]\n"
        f"Batch size  : [cyan]{config['batch_size']}[/]\n"
        f"Adapters → : [dim]{ADAPTERS_PATH}[/]\n\n"
        "[dim]First run will download the base model (~14GB)[/]\n"
        "[yellow]Press Ctrl+C to stop early — adapters are saved every 200 steps[/]",
        border_style="cyan"
    ))

    # Run mlx-lm training
    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", config["model"],
        "--train",
        "--data", config["data"],
        "--batch-size", str(config["batch_size"]),
        "--iters", str(config["iters"]),
        "--val-batches", str(config["val_batches"]),
        "--learning-rate", str(config["learning_rate"]),
        "--steps-per-report", str(config["steps_per_report"]),
        "--steps-per-eval", str(config["steps_per_eval"]),
        "--save-every", str(config["save_every"]),
        "--adapter-path", config["adapter_path"],
        "--lora-layers", str(config["lora_layers"]),
        "--seed", str(config["seed"]),
    ]

    if config.get("grad_checkpoint"):
        cmd.append("--grad-checkpoint")

    console.print(f"[dim]Command: {' '.join(cmd)}[/]\n")

    try:
        process = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Training failed with exit code {e.returncode}[/]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Training interrupted. Adapters saved up to last checkpoint.[/]")


def fuse_model():
    """Fuse LoRA adapters into the base model for standalone deployment."""
    console.print(Panel(
        "[bold]Fusing LoRA adapters into base model[/]\n\n"
        f"Base model : [cyan]{MLX_MODEL}[/]\n"
        f"Adapters   : [dim]{ADAPTERS_PATH}[/]\n"
        f"Output     : [dim]{FUSED_PATH}[/]\n\n"
        "[dim]This creates a standalone model you can use with Ollama[/]",
        border_style="cyan"
    ))

    FUSED_PATH.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "mlx_lm.fuse",
        "--model", str(MLX_MODEL),
        "--adapter-path", str(ADAPTERS_PATH),
        "--save-path", str(FUSED_PATH),
        "--upload-repo", "",  # don't upload
    ]

    try:
        subprocess.run(cmd, check=True)
        console.print(Panel(
            "[bold green]Model fused successfully![/]\n\n"
            f"Fused model saved to: [bold]{FUSED_PATH}[/]\n\n"
            "To use the fine-tuned model with Ollama:\n"
            "  1. Convert: [bold]python scripts/export_ollama.py[/]\n"
            "  2. Chat:    [bold]python scripts/chat.py[/]",
            title="Fuse Complete ✓",
            border_style="green"
        ))
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Fuse failed: {e}[/]")


def test_adapter():
    """Quick test of the fine-tuned model with a sample prompt."""
    console.print("\n[bold]Testing fine-tuned model...[/]\n")

    test_prompt = (
        "<s>[INST] What is the significance of peer review in scientific research? [/INST]"
    )

    cmd = [
        sys.executable, "-m", "mlx_lm.generate",
        "--model", str(MLX_MODEL),
        "--adapter-path", str(ADAPTERS_PATH),
        "--prompt", test_prompt,
        "--max-tokens", "200",
        "--temp", "0.1",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        console.print("[bold]Test output:[/]")
        console.print(Panel(result.stdout, border_style="green"))
    except subprocess.CalledProcessError:
        console.print("[yellow]Could not run test (model may still be valid)[/]")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Mistral 7B with LoRA on Apple Silicon")
    parser.add_argument("--iters", type=int, default=None,
                        help="Number of training iterations (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Batch size (default: 2; use 1 for 8GB Macs)")
    parser.add_argument("--lora-rank", type=int, default=None,
                        help="LoRA rank (default: 16; lower = less memory)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing adapter checkpoint")
    parser.add_argument("--fuse", action="store_true",
                        help="Fuse adapters into base model (run after training)")
    parser.add_argument("--test", action="store_true",
                        help="Test the fine-tuned model with a sample prompt")
    args = parser.parse_args()

    # Override config with CLI args
    config = LORA_CONFIG.copy()
    if args.iters:
        config["iters"] = args.iters
    if args.batch_size:
        config["batch_size"] = args.batch_size
    if args.lora_rank:
        config["lora_rank"] = args.lora_rank

    # ── Fuse mode ──────────────────────────────────────────────────────
    if args.fuse:
        fuse_model()
        return

    # ── Test mode ──────────────────────────────────────────────────────
    if args.test:
        test_adapter()
        return

    # ── Training mode ──────────────────────────────────────────────────
    console.print(Panel(
        "[bold cyan]Science LLM — Fine-tuning (LoRA + MLX)[/]\n"
        "Apple Silicon optimized  |  Model: Mistral 7B Instruct v0.3",
        border_style="cyan"
    ))

    check_prerequisites()
    show_config(config)

    # Check for YAML
    try:
        import yaml
    except ImportError:
        console.print("[yellow]Installing PyYAML...[/]")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml", "--quiet"])
        import yaml

    run_training(config)

    console.print(Panel(
        "[bold green]Training complete![/]\n\n"
        f"LoRA adapters saved to: [bold]{ADAPTERS_PATH}[/]\n\n"
        "Next steps:\n"
        "  Test model : [bold]python scripts/finetune.py --test[/]\n"
        "  Fuse model : [bold]python scripts/finetune.py --fuse[/]\n"
        "  Chat (RAG) : [bold]python scripts/chat.py[/]",
        title="Done ✓",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
