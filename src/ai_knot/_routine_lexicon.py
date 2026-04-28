"""Activity / routine vocabulary normalizer.

Maps activity stems to canonical routine categories used in canonical_surface
enrichment.  Covers outdoor, camping, family, fitness, and social routines.
Generic English vocabulary — no proper nouns.
"""

from __future__ import annotations

# stem (lowercase substring) → canonical routine label
STEM_TO_ROUTINE: dict[str, str] = {
    # Camping / fire activities
    "roast": "roasting",
    "campfire": "campfire",
    "marshmallow": "roasting",
    "s'more": "roasting",
    "bonfire": "campfire",
    "fireside": "campfire",
    # Storytelling / social
    "story": "storytelling",
    "stories": "storytelling",
    "tale": "storytelling",
    "tales": "storytelling",
    "narrat": "storytelling",
    "anecdote": "storytelling",
    # Hiking / outdoor
    "hike": "hiking",
    "hiking": "hiking",
    "trail": "hiking",
    "trek": "hiking",
    "backpack": "hiking",
    "nature walk": "hiking",
    # Family routines
    "family time": "family_time",
    "family outing": "family_time",
    "family hike": "hiking",
    "family trip": "family_time",
    # Picnic / outdoors gathering
    "picnic": "picnic",
    "cookout": "cookout",
    "barbecue": "cookout",
    "grill": "cookout",
    # Sports / fitness routines
    "workout": "workout",
    "exercise": "exercise",
    "jog": "jogging",
    "yoga": "yoga",
    "meditat": "meditation",
    # Creative routines
    "journaling": "journaling",
    "journal": "journaling",
    "diari": "journaling",
    "sketch": "sketching",
    "doodle": "sketching",
    # Social routines
    "game night": "game_night",
    "board game": "game_night",
    "movie night": "movie_night",
    "dinner party": "dinner_party",
}
