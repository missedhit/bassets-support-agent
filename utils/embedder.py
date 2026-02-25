"""
Embedding utility using Voyage AI.

Voyage AI is Anthropic's recommended embedding provider.
Model: voyage-3 (1024 dimensions, excellent for retrieval).
"""

import time
from typing import Optional

import voyageai

from config import VOYAGE_API_KEY, VOYAGE_MODEL, EMBEDDING_BATCH_SIZE


_client: Optional[voyageai.Client] = None


def get_client() -> voyageai.Client:
    """Lazy-initialize the Voyage AI client."""
    global _client
    if _client is None:
        if not VOYAGE_API_KEY:
            raise ValueError(
                "VOYAGE_API_KEY not set. Add it to your .env file. "
                "Get a key at https://dash.voyageai.com/"
            )
        _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def embed_texts(
    texts: list[str],
    input_type: str = "document",
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        input_type: "document" for ingestion, "query" for search queries.
                    Voyage optimizes embeddings differently for each.
        batch_size: Number of texts per API call.

    Returns:
        List of embedding vectors (each is a list of floats).
    """
    client = get_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        # Retry with backoff on rate limits
        for attempt in range(3):
            try:
                result = client.embed(
                    texts=batch,
                    model=VOYAGE_MODEL,
                    input_type=input_type,
                )
                all_embeddings.extend(result.embeddings)
                break
            except Exception as e:
                if "rate" in str(e).lower() and attempt < 2:
                    wait = (attempt + 1) * 5
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        # Small delay between batches to avoid rate limits
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_embeddings


def embed_query(query: str) -> list[float]:
    """
    Embed a single search query.
    Uses input_type="query" for retrieval-optimized embedding.
    """
    embeddings = embed_texts([query], input_type="query")
    return embeddings[0]
