"""
preprocess.py  —  Clean Mathpix markdown files before ingestion
================================================================
Strips noise from Mathpix-converted scientific papers:
  - References / Bibliography section
  - Acknowledgements / Funding sections
  - Page numbers and running headers/footers
  - Repeated whitespace and artifacts
  - Optional: figure/table captions

Reads all .md files from ./docs/raw/ and writes cleaned versions
to ./docs/  (the folder watched by ingest.py).

Mathpix workflow:
  1. Open PDF in Mathpix Snipping Tool → export as Markdown (.md)
  2. Save exported .md files into ./docs/raw/
  3. Run:  python scripts/preprocess.py
  4. Run:  python scripts/ingest.py

Usage:
    python scripts/preprocess.py
    python scripts/preprocess.py --input docs/raw --output docs/clean
    python scripts/preprocess.py --keep-refs        # don't strip references
    python scripts/preprocess.py --keep-captions    # keep figure captions
    python scripts/preprocess.py --dry-run          # preview without saving
"""

import re
import argparse
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ── Default paths ──────────────────────────────────────────────────────────
RAW_PATH   = Path("./docs/raw")     # drop Mathpix .md files here
CLEAN_PATH = Path("./docs")         # ingest.py reads from here


# ── Section headers that signal "remove everything below this line" ─────────
STRIP_SECTION_PATTERNS = [
    # References
    r"^#{1,4}\s*(references|bibliography|works cited|citations)\s*$",
    # Acknowledgements
    r"^#{1,4}\s*(acknowledgements?|acknowledgments?|funding|conflict of interest"
    r"|competing interests?|author contributions?|data availability"
    r"|supplementary|appendix\s*[a-z]?)\s*$",
]

# ── Line-level patterns to remove entirely ─────────────────────────────────
REMOVE_LINE_PATTERNS = [
    # Standalone page numbers (digit-only lines, optionally with dashes/dots)
    r"^[\s\-–—·•]*\d{1,4}[\s\-–—·•]*$",
    # DOI / URL-only lines
    r"^https?://\S+$",
    r"^doi:\s*\S+$",
    r"^DOI:\s*\S+$",
    # Received/Accepted/Published stamps
    r"^(Received|Accepted|Published|Available online|Revised)\s*:?\s*\d",
    # Copyright lines
    r"^©\s*\d{4}",
    r"^Copyright\s+©",
    # Journal header artifacts (e.g. "Journal of Astronomy  Vol. 12")
    r"^[A-Z][A-Za-z\s]+Vol\.\s*\d+",
    # Mathpix artifact: lone equation label lines like "(1)" or "[1]"
    r"^\s*[\(\[]\d+[\)\]]\s*$",
]

# ── Figure / table caption patterns (optional removal) ─────────────────────
CAPTION_PATTERNS = [
    r"^(Fig(?:ure)?\.?\s*\d+[\.:]\s*.*)",
    r"^(Table\s*\d+[\.:]\s*.*)",
    r"^(Scheme\s*\d+[\.:]\s*.*)",
]


def strip_trailing_section(text: str, patterns: list[str]) -> tuple[str, list[str]]:
    """
    Find the first heading matching any pattern and remove it + everything after.
    Returns (cleaned_text, list_of_stripped_section_titles).
    """
    lines = text.splitlines()
    stripped = []

    for i, line in enumerate(lines):
        for pat in patterns:
            if re.match(pat, line.strip(), re.IGNORECASE):
                stripped.append(line.strip())
                return "\n".join(lines[:i]), stripped

    return text, stripped


def remove_line_noise(text: str, remove_captions: bool = False) -> tuple[str, int]:
    """Remove noisy lines. Returns (cleaned_text, lines_removed_count)."""
    patterns = REMOVE_LINE_PATTERNS[:]
    if remove_captions:
        patterns += CAPTION_PATTERNS

    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    lines = text.splitlines()
    kept, removed = [], 0

    for line in lines:
        if any(p.match(line.strip()) for p in compiled):
            removed += 1
        else:
            kept.append(line)

    return "\n".join(kept), removed


def clean_whitespace(text: str) -> str:
    """Normalize excessive blank lines and trailing spaces."""
    # Remove trailing spaces on each line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove blank lines immediately after a heading
    text = re.sub(r"(^#{1,6}.+)\n\n+(?=\S)", r"\1\n", text, flags=re.MULTILINE)
    return text.strip()


def clean_mathpix_artifacts(text: str) -> str:
    """Fix common Mathpix export quirks."""
    # Mathpix sometimes wraps inline math with extra spaces: $ x $ → $x$
    text = re.sub(r"\$\s+([^$]+?)\s+\$", r"$\1$", text)
    # Remove stray backslashes at end of lines (Mathpix line-break artifact)
    text = re.sub(r"\\\s*$", "", text, flags=re.MULTILINE)
    # Collapse "- \n" soft hyphen line breaks from PDF columns
    text = re.sub(r"-\s*\n\s*([a-z])", r"\1", text)
    # Fix "et al ." → "et al."
    text = re.sub(r"\bet al\s+\.", "et al.", text)
    return text


def process_file(
    src: Path,
    dst: Path,
    keep_refs: bool,
    keep_captions: bool,
    dry_run: bool,
) -> dict:
    """Process one Mathpix markdown file. Returns stats dict."""
    original = src.read_text(encoding="utf-8", errors="ignore")
    text = original
    stats = {
        "file": src.name,
        "original_lines": len(original.splitlines()),
        "stripped_sections": [],
        "lines_removed": 0,
    }

    # 1. Strip trailing sections (refs, acknowledgements, etc.)
    if not keep_refs:
        text, stripped = strip_trailing_section(text, STRIP_SECTION_PATTERNS)
        stats["stripped_sections"] = stripped

    # 2. Remove noisy lines
    text, n_removed = remove_line_noise(text, remove_captions=not keep_captions)
    stats["lines_removed"] = n_removed

    # 3. Fix Mathpix artifacts
    text = clean_mathpix_artifacts(text)

    # 4. Final whitespace cleanup
    text = clean_whitespace(text)

    stats["final_lines"] = len(text.splitlines())
    stats["reduction_pct"] = round(
        100 * (1 - stats["final_lines"] / max(stats["original_lines"], 1)), 1
    )

    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean Mathpix markdown files before ingestion"
    )
    parser.add_argument(
        "--input", type=Path, default=RAW_PATH,
        help="Folder containing raw Mathpix .md files (default: ./docs/raw)"
    )
    parser.add_argument(
        "--output", type=Path, default=CLEAN_PATH,
        help="Folder to write cleaned .md files (default: ./docs)"
    )
    parser.add_argument(
        "--keep-refs", action="store_true",
        help="Keep the References/Bibliography section"
    )
    parser.add_argument(
        "--keep-captions", action="store_true",
        help="Keep figure and table captions"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing any files"
    )
    args = parser.parse_args()

    # ── Find source files ──────────────────────────────────────────────
    if not args.input.exists():
        console.print(Panel(
            f"[yellow]Input folder not found:[/] [bold]{args.input}[/]\n\n"
            "Create it and place your Mathpix .md files inside:\n"
            f"  [bold]mkdir -p {args.input}[/]\n\n"
            "Then export from Mathpix Snipping Tool as Markdown and save there.",
            title="No input folder",
            border_style="yellow"
        ))
        return

    md_files = sorted(args.input.rglob("*.md"))
    if not md_files:
        console.print(Panel(
            f"[yellow]No .md files found in [bold]{args.input}[/][/]\n\n"
            "Export your PDFs from Mathpix Snipping Tool as Markdown (.md)\n"
            f"and place them in [bold]{args.input}/[/]",
            title="Nothing to process",
            border_style="yellow"
        ))
        return

    mode = "[dim](dry run — no files written)[/]" if args.dry_run else ""
    console.print(Panel(
        f"[bold cyan]Mathpix Markdown Preprocessor[/] {mode}\n"
        f"Input  : [dim]{args.input}[/]\n"
        f"Output : [dim]{args.output}[/]\n"
        f"Files  : [bold]{len(md_files)}[/]\n"
        f"Strip references  : [bold]{'No' if args.keep_refs else 'Yes'}[/]\n"
        f"Strip captions    : [bold]{'No' if args.keep_captions else 'Yes'}[/]",
        border_style="cyan"
    ))

    # ── Process files ──────────────────────────────────────────────────
    all_stats = []
    for src in md_files:
        # Mirror subdirectory structure in output
        rel = src.relative_to(args.input)
        dst = args.output / rel

        stats = process_file(
            src, dst,
            keep_refs=args.keep_refs,
            keep_captions=args.keep_captions,
            dry_run=args.dry_run,
        )
        all_stats.append(stats)

        # Per-file summary
        sections_note = ""
        if stats["stripped_sections"]:
            sections_note = f" | removed: {', '.join(stats['stripped_sections'])}"
        console.log(
            f"  [green]{stats['file']}[/]: "
            f"{stats['original_lines']} → {stats['final_lines']} lines "
            f"([cyan]-{stats['reduction_pct']}%[/]){sections_note}"
        )

    # ── Summary table ──────────────────────────────────────────────────
    table = Table(title="Processing Summary", border_style="cyan", show_lines=True)
    table.add_column("File",            style="bold")
    table.add_column("Original lines",  justify="right")
    table.add_column("Final lines",     justify="right")
    table.add_column("Reduction",       justify="right", style="cyan")
    table.add_column("Sections stripped")

    for s in all_stats:
        table.add_row(
            s["file"],
            str(s["original_lines"]),
            str(s["final_lines"]),
            f"-{s['reduction_pct']}%",
            ", ".join(s["stripped_sections"]) or "—",
        )
    console.print(table)

    if args.dry_run:
        console.print("[yellow]Dry run complete. No files were written.[/]")
    else:
        console.print(Panel(
            f"[bold green]Done![/] {len(all_stats)} file(s) cleaned → [bold]{args.output}[/]\n\n"
            "Next step:\n"
            "  [bold]python scripts/ingest.py[/]",
            title="Complete ✓",
            border_style="green"
        ))


if __name__ == "__main__":
    main()
