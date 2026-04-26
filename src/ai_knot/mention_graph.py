"""Mention Graph — entity extraction and 1-hop expansion for recall.

Extracts named entities from fact content at ingest time and builds an
entity→fact index.  At recall time, query entities are expanded via 1-hop
to retrieve facts that mention related entities (aliases, co-occurring names).

Activated by setting AI_KNOT_MENTION_GRAPH=1.

Entity extraction uses conservative proper-noun heuristics (no LLM, no NLP
library): capitalized words ≥ 3 chars that are not common non-entity tokens.
This keeps extraction fast and avoids adding new dependencies.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_knot.storage.base import StorageBackend

MENTION_GRAPH_ENABLED: bool = os.environ.get("AI_KNOT_MENTION_GRAPH", "").strip() in {
    "1",
    "true",
    "yes",
}

# Conservative skip-list: common words that appear capitalised in conversation
# text but are NOT named entities.  Sorted for readability only.
_NON_ENTITIES: frozenset[str] = frozenset(
    {
        "Also",
        "Alright",
        "Amazing",
        "And",
        "Anything",
        "Appreciate",
        "Awesome",
        "But",
        "Check",
        "Congrats",
        "Cool",
        "Did",
        "Does",
        "Done",
        "Each",
        "Even",
        "Every",
        "For",
        "Glad",
        "Got",
        "Great",
        "Hang",
        "Have",
        "Her",
        "Here",
        "Hey",
        "His",
        "Hope",
        "How",
        "Its",
        "Just",
        "Let",
        "Love",
        "Meet",
        "More",
        "Much",
        "My",
        "Nice",
        "Now",
        "Oh",
        "Okay",
        "Our",
        "Sounds",
        "Sorry",
        "Sure",
        "That",
        "Thanks",
        "Their",
        "There",
        "This",
        "Those",
        "Though",
        "Too",
        "Very",
        "Want",
        "Was",
        "Well",
        "What",
        "When",
        "Where",
        "Which",
        "Who",
        "Why",
        "With",
        "Wow",
        "Yeah",
        "Yes",
        "You",
        "Your",
        # Calendar tokens
        "April",
        "August",
        "December",
        "February",
        "Friday",
        "January",
        "July",
        "June",
        "March",
        "May",
        "Monday",
        "November",
        "October",
        "Saturday",
        "September",
        "Sunday",
        "Thursday",
        "Tuesday",
        "Wednesday",
    }
)

# Match capitalised words ≥ 3 chars; excludes all-caps abbreviations.
_ENTITY_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")


def extract_entities(text: str) -> list[str]:
    """Extract likely named entities (persons/places) from raw text.

    Uses simple proper-noun heuristics.  Returns a deduplicated list.
    """
    raw = _ENTITY_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for w in raw:
        if w not in _NON_ENTITIES and w not in seen:
            seen.add(w)
            result.append(w)
    return result


def index_fact_entities(
    agent_id: str,
    fact_id: str,
    content: str,
    storage: StorageBackend,
) -> None:
    """Extract entities from *content* and store them in the mention graph.

    Called at ingest time (in ``KnowledgeBase.add``).  No-op when storage
    backend does not support ``store_mention``.
    """
    if not hasattr(storage, "store_mention"):
        return
    entities = extract_entities(content)
    for entity in entities:
        storage.store_mention(agent_id, entity, fact_id, confidence=1.0)


def hop_expand(
    query: str,
    agent_id: str,
    storage: StorageBackend,
) -> set[str]:
    """Return fact IDs reachable via 1-hop from query entities.

    Extracts named entities from *query*, looks up each entity in the mention
    graph, and returns all associated fact IDs.  The caller is responsible for
    intersecting with the active fact map and deduplicating.

    Returns empty set when storage does not support ``facts_for_entity``.
    """
    if not hasattr(storage, "facts_for_entity"):
        return set()
    entities = extract_entities(query)
    result: set[str] = set()
    for entity in entities:
        result.update(storage.facts_for_entity(agent_id, entity))
    return result
