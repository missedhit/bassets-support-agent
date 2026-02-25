#!/usr/bin/env python3
"""
Test the ingested knowledge base by running sample queries.

Usage:
    python test_query.py "How do I set up MACRS depreciation?"
    python test_query.py "installation requirements"
    python test_query.py --interactive

This runs vector search against Pinecone and shows the top matching chunks.
Useful for verifying your ingestion before building the full agent.
"""

import argparse
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PINECONE_API_KEY, PINECONE_INDEX_NAME
from utils.embedder import embed_query

console = Console()


def search(query: str, top_k: int = 5, product_area: str = None):
    """Search the knowledge base and display results."""
    from pinecone import Pinecone

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX_NAME)

    # Embed the query
    console.print(f"\n[dim]Embedding query...[/dim]")
    query_vector = embed_query(query)

    # Build filter if product area specified
    filter_dict = None
    if product_area:
        filter_dict = {"product_area": {"$eq": product_area}}

    # Search
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )

    # Display results
    console.print(f"\n[bold]Query:[/bold] {query}")
    if product_area:
        console.print(f"[bold]Filter:[/bold] product_area = {product_area}")
    console.print(f"[bold]Results:[/bold] {len(results.matches)}\n")

    for i, match in enumerate(results.matches):
        score = match.score
        meta = match.metadata or {}
        text = meta.get("text", "[no text stored]")

        # Color-code by relevance
        if score > 0.85:
            score_color = "green"
        elif score > 0.7:
            score_color = "yellow"
        else:
            score_color = "red"

        header = (
            f"[{score_color}]Score: {score:.4f}[/{score_color}] | "
            f"Source: {meta.get('source_type', '?')} | "
            f"File: {meta.get('source_file', '?')} | "
            f"Area: {meta.get('product_area', '?')}"
        )

        # Truncate long text for display
        display_text = text[:500] + "..." if len(text) > 500 else text

        console.print(Panel(
            display_text,
            title=f"Result {i + 1}",
            subtitle=header,
            border_style="dim",
        ))


def interactive():
    """Interactive query mode."""
    console.print("\n[bold blue]Bassets Knowledge Base - Interactive Query[/bold blue]")
    console.print("Type your question and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            query = console.input("[bold]> [/bold]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query or query.lower() in ('quit', 'exit', 'q'):
            break

        # Check for product area filter
        product_area = None
        if query.startswith("@"):
            parts = query.split(" ", 1)
            product_area = parts[0][1:]  # Remove @
            query = parts[1] if len(parts) > 1 else ""

        if query:
            search(query, product_area=product_area)

    console.print("\n[dim]Goodbye![/dim]")


def main():
    parser = argparse.ArgumentParser(description="Test queries against the Bassets knowledge base.")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    parser.add_argument("--area", "-a", help="Filter by product area")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    if args.interactive:
        interactive()
    elif args.query:
        search(args.query, top_k=args.top_k, product_area=args.area)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
