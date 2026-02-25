"""
RAG (Retrieval-Augmented Generation) pipeline.

This is the core of the support agent:
1. Take a customer question
2. Search Pinecone for relevant knowledge base chunks
3. Build a prompt with the retrieved context
4. Send to Claude API
5. Return the answer
"""

import time
from typing import Optional

import anthropic
from pinecone import Pinecone

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)
from utils.embedder import embed_query
from agent.prompts import SYSTEM_PROMPT, CONTEXT_TEMPLATE


# Lazy-initialized clients
_pinecone_index = None
_anthropic_client = None


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        _pinecone_index = pc.Index(PINECONE_INDEX_NAME)
    return _pinecone_index


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def retrieve_context(
    question: str,
    top_k: int = 6,
    score_threshold: float = 0.5,
    product_area: Optional[str] = None,
) -> list[dict]:
    """
    Search the knowledge base for chunks relevant to the question.

    Returns a list of dicts with keys: text, score, source_type, source_file, product_area
    """
    index = get_pinecone_index()

    # Embed the question (using "query" type for retrieval-optimized embedding)
    query_vector = embed_query(question)

    # Build optional filter
    filter_dict = None
    if product_area:
        filter_dict = {"product_area": {"$eq": product_area}}

    # Search Pinecone
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )

    # Filter by score threshold and extract
    chunks = []
    for match in results.matches:
        if match.score < score_threshold:
            continue

        meta = match.metadata or {}
        chunks.append({
            "text": meta.get("text", ""),
            "score": match.score,
            "source_type": meta.get("source_type", "unknown"),
            "source_file": meta.get("source_file", "unknown"),
            "product_area": meta.get("product_area", "general"),
            "section": meta.get("section", ""),
        })

    return chunks


def build_context_block(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context block for the prompt.
    """
    if not chunks:
        return "[No relevant knowledge base content found for this question.]"

    parts = []
    for i, chunk in enumerate(chunks, 1):
        source_label = chunk["source_type"].replace("_", " ").title()
        section = f" - {chunk['section']}" if chunk.get("section") else ""
        header = f"[Source {i}: {source_label} ({chunk['source_file']}{section})]"
        parts.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(parts)


def generate_answer(
    question: str,
    conversation_history: Optional[list[dict]] = None,
    top_k: int = 6,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1024,
    stream: bool = False,
) -> dict:
    """
    Full RAG pipeline: retrieve context, build prompt, call Claude.

    Args:
        question: The customer's question.
        conversation_history: Optional list of previous messages for multi-turn.
            Each item: {"role": "user"|"assistant", "content": "..."}
        top_k: Number of knowledge base chunks to retrieve.
        model: Claude model to use.
        max_tokens: Max tokens in Claude's response.
        stream: If True, returns a streaming response iterator.

    Returns:
        dict with keys: answer, sources, model, retrieval_time_ms, generation_time_ms
        If stream=True, returns a dict with "stream" key containing the iterator.
    """
    # Step 1: Retrieve relevant context
    t0 = time.time()
    chunks = retrieve_context(question, top_k=top_k)
    retrieval_ms = int((time.time() - t0) * 1000)

    # Step 2: Build the context block
    context_block = build_context_block(chunks)

    # Step 3: Build messages
    messages = []

    # Add conversation history if provided (for multi-turn)
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 turns max
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Add the current question with context
    user_message = CONTEXT_TEMPLATE.format(
        context=context_block,
        question=question,
    )
    messages.append({"role": "user", "content": user_message})

    # Step 4: Call Claude
    client = get_anthropic_client()
    t1 = time.time()

    if stream:
        # Return streaming response
        stream_response = client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return {
            "stream": stream_response,
            "sources": _format_sources(chunks),
            "retrieval_time_ms": retrieval_ms,
        }

    # Non-streaming response
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    generation_ms = int((time.time() - t1) * 1000)

    answer = response.content[0].text if response.content else "I was unable to generate a response. Please try again."

    return {
        "answer": answer,
        "sources": _format_sources(chunks),
        "model": model,
        "retrieval_time_ms": retrieval_ms,
        "generation_time_ms": generation_ms,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


def _format_sources(chunks: list[dict]) -> list[dict]:
    """Format chunk metadata into a clean sources list for the response."""
    sources = []
    seen = set()
    for chunk in chunks:
        key = (chunk["source_file"], chunk.get("section", ""))
        if key not in seen:
            seen.add(key)
            sources.append({
                "file": chunk["source_file"],
                "type": chunk["source_type"],
                "area": chunk["product_area"],
                "section": chunk.get("section", ""),
                "relevance": round(chunk["score"], 3),
            })
    return sources
