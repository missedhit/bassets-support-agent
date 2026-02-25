"""
Auto-tag document chunks with Bassets product areas.

Uses keyword matching to assign each chunk to one or more product areas.
This metadata enables filtered retrieval (e.g., only search depreciation docs).
"""

from config import PRODUCT_AREAS


def tag_product_area(text: str) -> str:
    """
    Determine the primary product area for a text chunk.

    Returns the product area with the highest keyword match count.
    Falls back to "general" if no strong match.
    """
    text_lower = text.lower()
    scores = {}

    for area, keywords in PRODUCT_AREAS.items():
        if not keywords:  # Skip "general" (it's the fallback)
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[area] = score

    if not scores:
        return "general"

    # Return the area with the highest score
    return max(scores, key=scores.get)


def tag_all_product_areas(text: str) -> list[str]:
    """
    Return all matching product areas for a text chunk (not just the primary).
    Useful for multi-topic documents.
    """
    text_lower = text.lower()
    areas = []

    for area, keywords in PRODUCT_AREAS.items():
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score >= 2:  # Require at least 2 keyword matches for secondary areas
            areas.append(area)

    return areas if areas else ["general"]
