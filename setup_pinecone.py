"""
One-time setup: Create the Pinecone index for the Bassets support agent.

Run this once before your first ingestion:
    python setup_pinecone.py

The index uses cosine similarity with 1024 dimensions (Voyage AI voyage-3 model).
"""

import sys
from pinecone import Pinecone, ServerlessSpec

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_CLOUD,
    PINECONE_REGION,
    EMBEDDING_DIMENSION,
)


def setup():
    if not PINECONE_API_KEY:
        print("ERROR: PINECONE_API_KEY not set. Add it to your .env file.")
        print("Get a free key at https://app.pinecone.io/")
        sys.exit(1)

    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index already exists
    existing = [idx.name for idx in pc.list_indexes()]

    if PINECONE_INDEX_NAME in existing:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists.")
        index = pc.Index(PINECONE_INDEX_NAME)
        stats = index.describe_index_stats()
        print(f"  Vectors: {stats.total_vector_count}")
        print(f"  Dimension: {stats.dimension}")
        print("Ready to ingest!")
        return

    print(f"Creating index '{PINECONE_INDEX_NAME}'...")
    print(f"  Cloud: {PINECONE_CLOUD}")
    print(f"  Region: {PINECONE_REGION}")
    print(f"  Dimensions: {EMBEDDING_DIMENSION}")
    print(f"  Metric: cosine")

    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION,
        ),
    )

    print(f"Index '{PINECONE_INDEX_NAME}' created successfully!")
    print("You can now run: python ingest.py --source ./data")


if __name__ == "__main__":
    setup()
