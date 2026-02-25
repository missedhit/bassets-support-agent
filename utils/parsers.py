"""
Document parsers for different source types.

Each parser returns a list of Document objects with text content and metadata.
"""

import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


@dataclass
class Document:
    """A parsed document ready for chunking and embedding."""
    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PDF Parser
# ---------------------------------------------------------------------------

def parse_pdf(file_path: str) -> list[Document]:
    """
    Parse a PDF file into documents (one per page or logical section).

    Handles multi-column layouts, headers/footers, and table-like content.
    Groups pages into logical sections when headings are detected.
    """
    file_path = Path(file_path)
    docs = []

    try:
        pdf = fitz.open(str(file_path))
    except Exception as e:
        print(f"  ERROR: Could not open PDF {file_path.name}: {e}")
        return []

    current_section = ""
    current_text = []

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        text = page.get_text("text")

        if not text or not text.strip():
            continue

        # Clean up common PDF artifacts
        text = _clean_pdf_text(text)

        # Check if this page starts a new section (has a prominent heading)
        heading = _detect_heading(text)

        if heading and current_text:
            # Save previous section
            combined = "\n\n".join(current_text)
            if combined.strip():
                docs.append(Document(
                    text=combined,
                    metadata={
                        "source_type": "pdf",
                        "source_file": file_path.name,
                        "section": current_section or "Introduction",
                    }
                ))
            current_text = [text]
            current_section = heading
        else:
            current_text.append(text)
            if heading and not current_section:
                current_section = heading

    # Don't forget the last section
    if current_text:
        combined = "\n\n".join(current_text)
        if combined.strip():
            docs.append(Document(
                text=combined,
                metadata={
                    "source_type": "pdf",
                    "source_file": file_path.name,
                    "section": current_section or "General",
                }
            ))

    pdf.close()
    print(f"  Parsed {file_path.name}: {len(docs)} sections from {page_num + 1} pages")
    return docs


def _clean_pdf_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""
    # Remove excessive whitespace but preserve paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove page numbers at start/end of pages
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Remove common headers/footers (customize for Bassets docs)
    text = re.sub(r'(?i)^\s*(bassets\s+fixed\s+assets?|page\s+\d+|confidential)\s*$', '', text, flags=re.MULTILINE)
    return text.strip()


def _detect_heading(text: str) -> Optional[str]:
    """Detect if text starts with a heading-like line."""
    first_line = text.strip().split('\n')[0].strip()
    # Heuristic: short line, possibly uppercase or title case, no period at end
    if (
        len(first_line) < 80
        and not first_line.endswith('.')
        and (first_line.isupper() or first_line.istitle() or first_line.startswith('Chapter'))
    ):
        return first_line
    return None


# ---------------------------------------------------------------------------
# Zoho Desk Export Parser
# ---------------------------------------------------------------------------

def parse_zoho_tickets(file_path: str) -> list[Document]:
    """
    Parse a Zoho Desk ticket export CSV.

    Expected columns (flexible matching):
    - Subject / Ticket Subject
    - Description / Ticket Description
    - Resolution / Solution / Comments
    - Status
    - Category / Classification
    """
    file_path = Path(file_path)
    docs = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]

        # Flexible column mapping
        col_map = _map_zoho_columns(headers, reader.fieldnames or [])

        if not col_map.get('subject'):
            print(f"  WARNING: Could not find 'Subject' column in {file_path.name}")
            print(f"  Available columns: {reader.fieldnames}")
            return []

        row_count = 0
        for row in reader:
            subject = _get_col(row, col_map, 'subject', '')
            description = _get_col(row, col_map, 'description', '')
            resolution = _get_col(row, col_map, 'resolution', '')
            status = _get_col(row, col_map, 'status', '')
            category = _get_col(row, col_map, 'category', '')

            # Only include resolved/closed tickets (they have useful answers)
            if status.lower() not in ('resolved', 'closed', 'answered', ''):
                continue

            # Build a Q&A style document from the ticket
            parts = []
            if subject:
                parts.append(f"Question: {subject}")
            if description:
                parts.append(f"Details: {description}")
            if resolution:
                parts.append(f"Answer: {resolution}")

            text = "\n\n".join(parts)
            if text.strip() and len(text) > 50:  # Skip near-empty tickets
                docs.append(Document(
                    text=text,
                    metadata={
                        "source_type": "zoho_ticket",
                        "source_file": file_path.name,
                        "category": category,
                        "status": status,
                    }
                ))
                row_count += 1

    print(f"  Parsed {file_path.name}: {row_count} resolved tickets")
    return docs


def parse_zoho_kb_articles(file_path: str) -> list[Document]:
    """
    Parse a Zoho Desk Knowledge Base export CSV.

    Expected columns:
    - Title
    - Content / Answer / Body
    - Category / Section
    """
    file_path = Path(file_path)
    docs = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]

        col_map = _map_zoho_kb_columns(headers, reader.fieldnames or [])

        row_count = 0
        for row in reader:
            title = _get_col(row, col_map, 'title', '')
            content = _get_col(row, col_map, 'content', '')
            category = _get_col(row, col_map, 'category', '')

            if not content.strip():
                continue

            # Strip HTML tags if present
            content = _strip_html(content)

            text = f"# {title}\n\n{content}" if title else content

            docs.append(Document(
                text=text,
                metadata={
                    "source_type": "zoho_kb",
                    "source_file": file_path.name,
                    "title": title,
                    "category": category,
                }
            ))
            row_count += 1

    print(f"  Parsed {file_path.name}: {row_count} KB articles")
    return docs


def _map_zoho_columns(headers: list[str], original: list[str]) -> dict:
    """Flexibly map Zoho ticket CSV columns."""
    mapping = {}
    for i, h in enumerate(headers):
        if 'subject' in h or 'title' in h:
            mapping['subject'] = original[i]
        elif 'description' in h and 'resolution' not in h:
            mapping['description'] = original[i]
        elif any(w in h for w in ['resolution', 'solution', 'answer', 'comment']):
            mapping['resolution'] = original[i]
        elif 'status' in h:
            mapping['status'] = original[i]
        elif any(w in h for w in ['category', 'classification', 'type']):
            mapping['category'] = original[i]
    return mapping


def _map_zoho_kb_columns(headers: list[str], original: list[str]) -> dict:
    """Flexibly map Zoho KB article CSV columns."""
    mapping = {}
    for i, h in enumerate(headers):
        if 'title' in h or 'name' in h:
            mapping['title'] = original[i]
        elif any(w in h for w in ['content', 'body', 'answer', 'text']):
            mapping['content'] = original[i]
        elif any(w in h for w in ['category', 'section', 'folder']):
            mapping['category'] = original[i]
    return mapping


def _get_col(row: dict, col_map: dict, key: str, default: str = '') -> str:
    """Safely get a mapped column value."""
    col_name = col_map.get(key)
    if col_name and col_name in row:
        return (row[col_name] or '').strip()
    return default


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Text / Markdown Parser
# ---------------------------------------------------------------------------

def parse_text_file(file_path: str) -> list[Document]:
    """
    Parse a plain text or markdown file.

    For markdown, splits on heading boundaries (# lines).
    For plain text, treats the whole file as one document.
    """
    file_path = Path(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.strip():
        return []

    ext = file_path.suffix.lower()
    source_type = "doc"

    # Markdown: split on headings
    if ext in ('.md', '.markdown'):
        docs = _split_markdown_sections(text, file_path.name)
    else:
        docs = [Document(
            text=text,
            metadata={
                "source_type": source_type,
                "source_file": file_path.name,
            }
        )]

    print(f"  Parsed {file_path.name}: {len(docs)} sections")
    return docs


def _split_markdown_sections(text: str, filename: str) -> list[Document]:
    """Split markdown into sections by headings."""
    sections = re.split(r'\n(?=#{1,3}\s)', text)
    docs = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract heading if present
        heading_match = re.match(r'^(#{1,3})\s+(.+)', section)
        heading = heading_match.group(2) if heading_match else ""

        docs.append(Document(
            text=section,
            metadata={
                "source_type": "doc",
                "source_file": filename,
                "section": heading,
            }
        ))

    return docs


# ---------------------------------------------------------------------------
# Transcript Parser
# ---------------------------------------------------------------------------

def parse_transcript(file_path: str) -> list[Document]:
    """
    Parse a call recording transcript.

    Handles common transcript formats:
    - Plain text (speaker labels optional)
    - Timestamped lines (e.g., from Whisper output)

    Cleans up filler words and normalizes speaker labels.
    """
    file_path = Path(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.strip():
        return []

    # Clean transcript
    text = _clean_transcript(text)

    docs = [Document(
        text=text,
        metadata={
            "source_type": "transcript",
            "source_file": file_path.name,
        }
    )]

    print(f"  Parsed {file_path.name}: {len(text)} characters")
    return docs


def _clean_transcript(text: str) -> str:
    """Clean up transcript text."""
    # Remove timestamps like [00:01:23] or (00:01:23)
    text = re.sub(r'[\[\(]\d{1,2}:\d{2}(?::\d{2})?[\]\)]', '', text)
    # Normalize speaker labels
    text = re.sub(r'^(Speaker\s*\d+|Agent|Customer|Support|Caller)\s*:', r'\1:', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove excessive filler words (keep some for naturalness)
    text = re.sub(r'\b(um|uh|like,?\s+you know)\b', '', text, flags=re.IGNORECASE)
    # Clean whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Auto-detect parser
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    '.pdf': 'pdf',
    '.csv': 'zoho',  # Default CSV to Zoho format
    '.txt': 'text',
    '.md': 'text',
    '.markdown': 'text',
}


def parse_file(file_path: str, file_type: Optional[str] = None) -> list[Document]:
    """
    Auto-detect file type and parse accordingly.

    Args:
        file_path: Path to the file.
        file_type: Override auto-detection. One of: pdf, zoho, zoho_kb, text, transcript

    Returns:
        List of Document objects.
    """
    path = Path(file_path)

    if not path.exists():
        print(f"  WARNING: File not found: {file_path}")
        return []

    # Determine parser
    if file_type:
        parser_key = file_type.lower()
    else:
        ext = path.suffix.lower()
        parser_key = SUPPORTED_EXTENSIONS.get(ext)

        if not parser_key:
            print(f"  SKIPPING: Unsupported file type: {path.name}")
            return []

    # Route to parser
    if parser_key == 'pdf':
        return parse_pdf(file_path)
    elif parser_key == 'zoho':
        return parse_zoho_tickets(file_path)
    elif parser_key == 'zoho_kb':
        return parse_zoho_kb_articles(file_path)
    elif parser_key in ('text', 'doc'):
        return parse_text_file(file_path)
    elif parser_key == 'transcript':
        return parse_transcript(file_path)
    else:
        print(f"  SKIPPING: Unknown parser type: {parser_key}")
        return []
