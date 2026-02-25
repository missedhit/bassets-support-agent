# Bassets.net AI Support Agent - Document Ingestion Pipeline

## Overview
This pipeline ingests documents from multiple sources (PDFs, Zoho Desk exports, text/markdown files, call transcripts) into a Pinecone vector database. The embeddings power a RAG-based support agent for Bassets.net customers.

## Architecture
```
[Source Documents] --> [Parser] --> [Chunker] --> [Embedder] --> [Pinecone]
     |                                                              |
     |-- PDFs (product manuals, guides)                             |
     |-- Zoho Desk CSV export (tickets, KB articles)                |
     |-- Text/Markdown files (Claude Project docs)                  |
     |-- Call transcripts (.txt from Whisper)                       |
                                                                    v
                                                        [Vector Index: bassets-support]
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 3. Create Pinecone index
```bash
python setup_pinecone.py
```

### 4. Run ingestion
```bash
# Ingest everything in the /data directory
python ingest.py --source ./data

# Ingest only PDFs
python ingest.py --source ./data/pdfs --type pdf

# Ingest Zoho Desk export
python ingest.py --source ./data/zoho_export.csv --type zoho

# Ingest call transcripts
python ingest.py --source ./data/transcripts --type transcript

# Dry run (no Pinecone writes, just see what would be ingested)
python ingest.py --source ./data --dry-run
```

## Data Directory Structure
Place your source files like this:
```
data/
  pdfs/              # Product manuals, user guides, release notes
  zoho/              # Zoho Desk CSV exports (tickets + KB articles)
  docs/              # Text/markdown files from Claude Project
  transcripts/       # Call recording transcripts (.txt)
```

## Zoho Desk Export Instructions
1. Go to Zoho Desk > Setup > Data Administration > Export
2. Export "Tickets" as CSV (include Subject, Description, Resolution, Status, Category)
3. Export "Knowledge Base Articles" as CSV
4. Place both files in `data/zoho/`

## Metadata
Each vector stored in Pinecone includes metadata for filtering:
- `source_type`: pdf | zoho_ticket | zoho_kb | doc | transcript
- `source_file`: original filename
- `chunk_index`: position within the document
- `product_area`: auto-tagged (e.g., "depreciation", "reporting", "installation")
- `date_ingested`: timestamp

## Re-ingestion
Running ingestion again on the same files will upsert (update existing vectors).
Vector IDs are deterministic based on source file + chunk index, so duplicates are avoided.
