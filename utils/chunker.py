"""
Smart text chunking for the ingestion pipeline.

Splits documents into overlapping chunks optimized for retrieval.
Respects sentence and paragraph boundaries where possible.
"""

import re
import tiktoken

from config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNK_SIZE


# Use cl100k_base tokenizer (same family as Claude/GPT-4 tokenizers)
_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a string."""
    return len(_encoder.encode(text))


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving whitespace."""
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    max_chunk_size: int = MAX_CHUNK_SIZE,
) -> list[str]:
    """
    Split text into overlapping chunks that respect sentence boundaries.

    Strategy:
    1. Split into paragraphs first
    2. Within each paragraph, split into sentences
    3. Greedily accumulate sentences until chunk_size is reached
    4. Include overlap from the end of the previous chunk

    Returns a list of text chunks.
    """
    if not text or not text.strip():
        return []

    # If the entire text fits in one chunk, return as-is
    if count_tokens(text) <= max_chunk_size:
        return [text.strip()]

    # Split into paragraphs, then sentences
    paragraphs = text.split("\n\n")
    all_sentences = []
    for para in paragraphs:
        sentences = split_into_sentences(para)
        if sentences:
            all_sentences.extend(sentences)
            # Add a paragraph break marker
            all_sentences.append("\n\n")

    # Remove trailing paragraph break
    if all_sentences and all_sentences[-1] == "\n\n":
        all_sentences.pop()

    # Greedily build chunks
    chunks = []
    current_chunk_sentences = []
    current_tokens = 0

    for sentence in all_sentences:
        sentence_tokens = count_tokens(sentence)

        # If a single sentence exceeds max, force-split it
        if sentence_tokens > max_chunk_size:
            # Flush current chunk first
            if current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = []
                current_tokens = 0

            # Brute-force split the long sentence by tokens
            tokens = _encoder.encode(sentence)
            for i in range(0, len(tokens), chunk_size):
                chunk_tokens = tokens[i : i + chunk_size]
                chunks.append(_encoder.decode(chunk_tokens))
            continue

        # Would adding this sentence exceed the target?
        if current_tokens + sentence_tokens > chunk_size and current_chunk_sentences:
            # Save current chunk
            chunks.append(" ".join(current_chunk_sentences))

            # Calculate overlap: take sentences from the end of current chunk
            overlap_sentences = []
            overlap_tokens = 0
            for s in reversed(current_chunk_sentences):
                s_tokens = count_tokens(s)
                if overlap_tokens + s_tokens > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tokens

            # Start new chunk with overlap
            current_chunk_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_chunk_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Don't forget the last chunk
    if current_chunk_sentences:
        last_chunk = " ".join(current_chunk_sentences)
        # Only add if it's meaningfully different from the previous chunk
        if not chunks or last_chunk != chunks[-1]:
            chunks.append(last_chunk)

    # Clean up whitespace
    chunks = [c.replace(" \n\n ", "\n\n").strip() for c in chunks]
    chunks = [c for c in chunks if c and count_tokens(c) > 10]  # Drop tiny fragments

    return chunks
