"""
pdf_to_md.py  —  Fast PDF → Markdown converter for text-based academic papers
==============================================================================
Uses PyMuPDF (fitz) to extract embedded text from PDFs — no OCR, no GPU,
no 4-hour waits. Works perfectly for any PDF with embedded text (all
standard published papers, journal articles, preprints, textbooks).

For scanned/image PDFs: keep using marker (slow but necessary).
Check with:  python scripts/pdf_to_md.py --check yourfile.pdf

Output goes to ./docs/raw/ so preprocess.py + ingest.py can pick it up.

Usage:
    python scripts/pdf_to_md.py paper.pdf
    python scripts/pdf_to_md.py ./papers/*.pdf        # batch
    python scripts/pdf_to_md.py --input-dir ./pdfs    # whole folder
    python scripts/pdf_to_md.py --check paper.pdf     # is OCR needed?
"""

import re
import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

RAW_PATH = Path("./docs/raw")


# ── Helpers ────────────────────────────────────────────────────────────────

def is_text_based(pdf_path: Path, sample_pages: int = 3) -> tuple[bool, float]:
    """
    Returns (is_text_based, avg_chars_per_page).
    If avg chars/page > 200, embedded text is present — no OCR needed.
    """
    import fitz
    doc   = fitz.open(str(pdf_path))
    pages = min(sample_pages, len(doc))
    total = sum(len(doc[i].get_text()) for i in range(pages))
    avg   = total / pages if pages else 0
    doc.close()
    return avg > 200, avg


def clean_extracted_text(text: str) -> str:
    """
    Fix common PDF text extraction artifacts:
      - Soft-hyphen line breaks:  "hyph-\nenation" → "hyphenation"
      - Ligatures:  ﬁ ﬂ ﬀ ff fi fl
      - Multiple spaces
      - Form-feed characters
    """
    # Ligatures
    ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi",
                 "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st", "Ĳ": "IJ", "ĳ": "ij"}
    for lig, rep in ligatures.items():
        text = text.replace(lig, rep)

    # Soft hyphen line breaks: word-\n  continuation → wordcontinuation
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)

    # Form feed / page markers
    text = text.replace("\x0c", "\n\n")

    # Excessive spaces (but NOT in math)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text


def extract_pages(pdf_path: Path) -> list[dict]:
    """
    Extract text page by page.
    Returns list of {page_num, text, width, height}.
    """
    import fitz
    doc   = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        # "text" mode preserves reading order better than default
        text = page.get_text("text", sort=True)
        pages.append({
            "page_num": i + 1,
            "text":     clean_extracted_text(text),
            "width":    page.rect.width,
            "height":   page.rect.height,
        })
    doc.close()
    return pages


def detect_sections(text: str) -> list[tuple[int, str]]:
    """
    Very rough section detection for academic papers.
    Returns list of (line_index, heading_text).
    """
    lines    = text.splitlines()
    headings = []

    # Patterns common in journal papers
    section_re = re.compile(
        r"^(\d+\.?\s+)?[A-Z][A-Za-z\s&,:]{3,60}$"
    )
    known = re.compile(
        r"^(Abstract|Introduction|Methods?|Methodology|Results?|Discussion|"
        r"Conclusions?|Summary|Background|Related Work|Acknowledgements?|"
        r"References?|Bibliography|Appendix|Data Availability|"
        r"Supplementary|Funding|Conflicts?)\b",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if known.match(line) or (section_re.match(line) and len(line) < 80):
            # Avoid false positives: skip lines ending with a period (body text)
            if not line.endswith(".") and not line.endswith(","):
                headings.append((i, line))

    return headings


def pages_to_markdown(pages: list[dict], title: str) -> str:
    """
    Combine all page texts into a clean markdown document.
    Adds a title heading and tries to detect section headings.
    """
    lines_out = [f"# {title}\n"]

    full_text = "\n\n".join(p["text"] for p in pages)

    # Detect candidate headings
    headings = detect_sections(full_text)
    heading_set = {h for _, h in headings}

    # Rebuild with markdown headings
    lines = full_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in heading_set:
            lines_out.append(f"\n## {stripped}\n")
        else:
            lines_out.append(line)

    return "\n".join(lines_out)


def convert_pdf(pdf_path: Path, output_dir: Path, force: bool = False) -> Path | None:
    """Convert one PDF to markdown. Returns output path or None on failure."""
    out_path = output_dir / (pdf_path.stem + ".md")

    if out_path.exists() and not force:
        console.log(f"  [dim]Skip (already exists): {out_path.name}[/]")
        return out_path

    # Check if text-based
    try:
        text_based, avg_chars = is_text_based(pdf_path)
    except Exception as e:
        console.log(f"  [red]Cannot open {pdf_path.name}: {e}[/]")
        return None

    if not text_based:
        console.log(
            f"  [yellow]⚠ {pdf_path.name}: low text ({avg_chars:.0f} chars/page) "
            f"— may be scanned. Consider using marker for OCR.[/]"
        )

    # Extract
    try:
        import fitz  # noqa
    except ImportError:
        console.print("[red]PyMuPDF not installed. Run: pip install pymupdf[/]")
        return None

    pages    = extract_pages(pdf_path)
    markdown = pages_to_markdown(pages, title=pdf_path.stem.replace("_", " "))

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────────────────

def cmd_check(pdf_paths: list[Path]):
    """Print whether each PDF needs OCR."""
    table = Table(title="PDF Text Check", border_style="cyan")
    table.add_column("File")
    table.add_column("Avg chars/page", justify="right")
    table.add_column("Needs OCR?", justify="center")
    table.add_column("Recommendation")

    for p in pdf_paths:
        try:
            text_based, avg = is_text_based(p)
            needs_ocr = not text_based
            rec = (
                "[green]pdf_to_md.py (fast)[/]" if text_based
                else "[yellow]marker (slow OCR)[/]"
            )
            table.add_row(
                p.name,
                f"{avg:.0f}",
                "[red]Yes[/]" if needs_ocr else "[green]No[/]",
                rec,
            )
        except Exception as e:
            table.add_row(p.name, "—", "—", f"[red]Error: {e}[/]")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Fast PDF→Markdown for text-based academic papers"
    )
    parser.add_argument("pdfs", nargs="*", type=Path,
                        help="PDF file(s) to convert")
    parser.add_argument("--input-dir", type=Path, default=None,
                        help="Convert all PDFs in this folder")
    parser.add_argument("--output-dir", type=Path, default=RAW_PATH,
                        help="Output directory for .md files (default: ./docs/raw)")
    parser.add_argument("--check", action="store_true",
                        help="Only check if PDFs need OCR, don't convert")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing .md files")
    args = parser.parse_args()

    # Collect files
    pdf_files: list[Path] = list(args.pdfs)
    if args.input_dir:
        pdf_files += sorted(args.input_dir.rglob("*.pdf"))

    if not pdf_files:
        console.print(Panel(
            "Provide PDF files or --input-dir.\n\n"
            "Examples:\n"
            "  [bold]python scripts/pdf_to_md.py paper.pdf[/]\n"
            "  [bold]python scripts/pdf_to_md.py --input-dir ~/Downloads/papers[/]\n"
            "  [bold]python scripts/pdf_to_md.py --check paper.pdf[/]",
            title="Usage", border_style="yellow"
        ))
        return

    if args.check:
        cmd_check(pdf_files)
        return

    # Convert
    console.print(Panel(
        f"[bold cyan]Fast PDF → Markdown Converter[/]\n"
        f"Files  : [bold]{len(pdf_files)}[/]\n"
        f"Output : [dim]{args.output_dir}[/]\n\n"
        "[dim]No OCR — uses embedded text. Seconds per file.[/]",
        border_style="cyan"
    ))

    results = []
    for pdf in pdf_files:
        console.log(f"Converting: [cyan]{pdf.name}[/]")
        out = convert_pdf(pdf, args.output_dir, force=args.force)
        if out:
            size_kb = out.stat().st_size // 1024
            console.log(f"  [green]✓[/] → {out.name} ({size_kb} KB)")
            results.append((pdf.name, out, True))
        else:
            results.append((pdf.name, None, False))

    ok  = sum(1 for _, _, s in results if s)
    fail = len(results) - ok

    console.print(Panel(
        f"[bold green]Done![/]  {ok} converted, {fail} failed\n"
        f"Output: [bold]{args.output_dir}[/]\n\n"
        "Next steps:\n"
        "  [bold]python scripts/preprocess.py[/]   ← clean the markdown\n"
        "  [bold]python scripts/ingest.py[/]        ← index into ChromaDB",
        title="Complete ✓", border_style="green"
    ))


if __name__ == "__main__":
    main()
