"""Visual / craft object vocabulary normalizer.

Maps object nouns to canonical object categories used in canonical_surface
enrichment.  Covers ceramics, pottery, painting subjects, and image objects.
Generic English vocabulary — no proper nouns.
"""

from __future__ import annotations

# stem (lowercase substring) → canonical object label
STEM_TO_OBJECT: dict[str, str] = {
    # Ceramics / pottery vessels
    "bowl": "bowl",
    " pot": "pot",
    " cup": "cup",
    "mug": "mug",
    "vase": "vase",
    "dish": "dish",
    "plate": "plate",
    "jar": "jar",
    "jug": "jug",
    "pitcher": "pitcher",
    "urn": "urn",
    # Pottery / ceramics process
    "potter": "pottery",
    "ceramic": "ceramics",
    "clay": "clay",
    "kiln": "kiln",
    "glaze": "glaze",
    "sculpt": "sculpture",
    # Painting subjects — nature
    "sunset": "sunset",
    "sunrise": "sunrise",
    "landscape": "landscape",
    "mountain": "mountain",
    "ocean": "ocean",
    "lake": "lake",
    "river": "river",
    "forest": "forest",
    "flower": "flower",
    "tree": "tree",
    # Animals (painting/photo subjects)
    "horse": "horse",
    "dog": "dog",
    "cat": "cat",
    "bird": "bird",
    # Art forms
    "portrait": "portrait",
    "still life": "still_life",
    "abstract": "abstract",
    "watercolor": "watercolor",
    "oil paint": "oil_painting",
    "sketch": "sketch",
    "charcoal": "charcoal",
    # Photography
    "photo": "photograph",
    "camera": "photograph",
    "snapshot": "photograph",
}
