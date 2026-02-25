#!/usr/bin/env python3
"""
Main ingestion script for the Bassets Support Agent knowledge base.

Usage:
    python ingest.py --source ./data                          # Ingest all files
    python ingest.py --source ./data/pdfs --type pdf          # Only PDFs
    python ingest.py --source ./data/zoho/tickets.csv --type zoho    # Zoho tickets
    python ingest.py --source ./data/zoho/kb.csv --type zoho_kb      # Zoho KB articles
    python ingest.py --source ./data/transcripts --type transcript   # Call transcripts
    python ingest.py --source ./data --dry-run                # Preview without writing

Pipeline:
    [Files] -> [Parse] -> [Chunk] -> [Tag] -> [Embed] -> [Upsert to Pinecone]
"""

import argparse
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PINECONE_API_KEY, PINECONE_INDEX_NAME
from utils.chunker import chunk_text, count_tokens
from utils.parsers import parse_file, Document, SUPPORTED_EXTENSIONS
from utils.tagger import tag_product_area

console = Console()


def generate_vector_id(source_file: str, chunk_index: int) -> str:
    """
    Generate a deterministic vector ID.
    Same file + same chunk position = same ID (enables upsert/dedup).
    """
    raw = f"{source_file}::chunk_{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def collect_files(source_path: str, file_type: str = None) -> list[tuple[str, str]]:
    """
    Collect all files to ingest from source path.
    Returns list of (file_path, parser_type) tuples.
    """
    source = Path(source_path)
    files = []

    if source.is_file():
        # Single file
        ext = source.suffix.lower()
        ptype = file_type or SUPPORTED_EXTENSIONS.get(ext, 'text')
        files.append((str(source), ptype))

    elif source.is_dir():
        # Directory: walk and collect supported files
        for root, dirs, filenames in os.walk(source):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for fname in sorted(filenames):
                if fname.startswith('.'):
                    continue

                fpath = os.path.join(root, fname)
                ext = Path(fname).suffix.lower()

                if file_type:
                    files.append((fpath, file_type))
                elif ext in SUPPORTED_EXTENSIONS:
                    # Auto-detect type, with smarter CSV handling
                    ptype = SUPPORTED_EXTENSIONS[ext]
                    # If CSV is in a folder called "kb" or filename contains "kb",
                    # treat as KB articles
                    if ext == '.csv' and ('kb' in fname.lower() or 'knowledge' in fname.lower()):
                        ptype = 'zoho_kb'
                    files.append((fpath, ptype))

                # Also handle transcript text files in transcript directories
                elif ext == '.txt' and 'transcript' in root.lower():
                    files.append((fpath, 'transcript'))
    else:
        console.print(f"[red]ERROR: Source path not found: {source_path}[/red]")
        sys.exit(1)

    return files


def ingest(
    source: str,
    file_type: str = None,
    dry_run: bool = False,
    batch_size: int = 50,
):
    """
    Main ingestion pipeline.

    1. Collect files
    2. Parse each file into documents
    3. Chunk documents
    4. Auto-tag chunks with product areas
    5. Generate embeddings
    6. Upsert to Pinecone
    """
    console.print("\n[bold blue]Bassets Support Agent - Document Ingestion[/bold blue]\n")

    # --- Step 1: Collect files ---
    files = collect_files(source, file_type)
    if not files:
        console.print("[yellow]No supported files found.[/yellow]")
        return

    console.print(f"Found [bold]{len(files)}[/bold] files to process\n")

    # --- Step 2 & 3: Parse and chunk ---
    all_chunks = []  # List of (chunk_text, metadata) tuples

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing files...", total=len(files))

        for file_path, ptype in files:
            progress.update(task, description=f"Parsing {Path(file_path).name}...")

            # Parse
            docs = parse_file(file_path, ptype)

            # Chunk each document
            for doc in docs:
                chunks = chunk_text(doc.text)
                for i, chunk in enumerate(chunks):
                    chunk_id = generate_vector_id(doc.metadata.get('source_file', file_path), len(all_chunks) + i)
                    product_area = tag_product_area(chunk)

                    metadata = {
                        **doc.metadata,
                        "chunk_index": i,
                        "product_area": product_area,
                        "date_ingested": datetime.now(timezone.utc).isoformat(),
                        "token_count": count_tokens(chunk),
                    }

                    all_chunks.append((chunk_id, chunk, metadata))

            progress.advance(task)

    console.print(f"\nTotal chunks: [bold]{len(all_chunks)}[/bold]")

    # --- Show summary ---
    summary = Table(title="Ingestion Summary")
    summary.add_column("Source Type", style="cyan")
    summary.add_column("Chunks", justify="right")
    summary.add_column("Product Areas")

    type_counts = {}
    area_counts = {}
    for _, _, meta in all_chunks:
        st = meta.get('source_type', 'unknown')
        pa = meta.get('product_area', 'general')
        type_counts[st] = type_counts.get(st, 0) + 1
        area_counts[pa] = area_counts.get(pa, 0) + 1

    for st, count in sorted(type_counts.items()):
        summary.add_row(st, str(count), "")

    summary.add_row("", "", "")
    for pa, count in sorted(area_counts.items()):
        summary.add_row("", str(count), pa)

    console.print(summary)

    if dry_run:
        console.print("\n[yellow]DRY RUN: No vectors written to Pinecone.[/yellow]")
        console.print("Remove --dry-run to write vectors.\n")

        # Show sample chunks
        console.print("[bold]Sample chunks:[/bold]\n")
        for chunk_id, text, meta in all_chunks[:3]:
            console.print(f"[dim]ID: {chunk_id}[/dim]")
            console.print(f"[dim]Meta: {meta}[/dim]")
            console.print(text[:300] + "..." if len(text) > 300 else text)
            console.print("---\n")
        return

    # --- Step 4: Embed ---
    if not all_chunks:
        console.print("[yellow]No chunks to embed.[/yellow]")
        return

    console.print(f"\nGenerating embeddings for {len(all_chunks)} chunks...")

    from utils.embedder import embed_texts

    chunk_texts = [text for _, text, _ in all_chunks]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding...", total=1)
        embeddings = embed_texts(chunk_texts, input_type="document")
        progress.advance(task)

    console.print(f"Generated [bold]{len(embeddings)}[/bold] embeddings")

    # --- Step 5: Upsert to Pinecone ---
    console.print(f"\nUpserting to Pinecone index '{PINECONE_INDEX_NAME}'...")

    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX_NAME)

    # Prepare vectors
    vectors = []
    for i, (chunk_id, text, meta) in enumerate(all_chunks):
        # Pinecone metadata: include the text for retrieval display
        # Truncate text in metadata to stay under Pinecone's 40KB limit
        meta_text = text[:8000] if len(text) > 8000 else text
        pine_meta = {
            **meta,
            "text": meta_text,
        }
        vectors.append({
            "id": chunk_id,
            "values": embeddings[i],
            "metadata": pine_meta,
        })

    # Upsert in batches
    upserted = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Upserting vectors...", total=len(vectors))

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            index.upsert(vectors=batch)
            upserted += len(batch)
            progress.update(task, completed=upserted)
            time.sleep(0.2)  # Small delay between batches

    # Final stats
    time.sleep(1)  # Let Pinecone catch up
    stats = index.describe_index_stats()
    console.print(f"\n[bold green]Done![/bold green]")
    console.print(f"Total vectors in index: [bold]{stats.total_vector_count}[/bold]\n")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into the Bassets Support Agent knowledge base."
    )
    parser.add_argument(
        "--source", "-s",
        required=True,
        help="Path to a file or directory to ingest.",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["pdf", "zoho", "zoho_kb", "text", "transcript"],
        default=None,
        help="Override auto-detected file type.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk only, don't embed or write to Pinecone.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Pinecone upsert batch size (default: 50).",
    )

    args = parser.parse_args()

    ingest(
        source=args.source,
        file_type=args.type,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
