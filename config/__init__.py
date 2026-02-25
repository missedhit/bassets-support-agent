"""
Configuration for the Bassets Support Agent ingestion pipeline.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Pinecone ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "bassets-support")
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"

# --- Voyage AI Embeddings ---
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = "voyage-3"  # Latest model, 1024 dimensions
EMBEDDING_DIMENSION = 1024
EMBEDDING_BATCH_SIZE = 32  # Voyage allows up to 128, but 32 is safer for large chunks

# --- Chunking ---
CHUNK_SIZE = 512          # Target tokens per chunk
CHUNK_OVERLAP = 64        # Overlap between chunks for context continuity
MAX_CHUNK_SIZE = 800      # Hard limit - never exceed this

# --- Bassets product areas for auto-tagging ---
PRODUCT_AREAS = {
    "depreciation": [
        "depreciation", "macrs", "straight-line", "declining balance",
        "sum-of-years", "section 179", "bonus depreciation", "useful life",
        "salvage value", "accumulated depreciation", "depreciation method",
        "half-year convention", "mid-quarter", "mid-month", "irs",
        "tax depreciation", "book depreciation", "amortization"
    ],
    "reporting": [
        "report", "reporting", "export", "print", "schedule",
        "depreciation schedule", "asset register", "fixed asset report",
        "audit", "audit trail", "crystal reports", "custom report"
    ],
    "installation": [
        "install", "installation", "setup", "configure", "system requirements",
        "database", "sql server", "network", "license", "activation",
        "update", "upgrade", "migration", "patch"
    ],
    "asset_management": [
        "asset", "fixed asset", "asset entry", "disposal", "transfer",
        "acquisition", "barcode", "asset tag", "inventory", "physical count",
        "asset class", "asset type", "location", "department", "custodian"
    ],
    "importing_data": [
        "import", "csv import", "excel import", "data migration",
        "mass import", "bulk upload", "template", "import wizard",
        "convert", "conversion"
    ],
    "general": []  # Fallback
}
