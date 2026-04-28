"""Tests for ValueNormalizer lexicons and canonical surface enrichment."""

from __future__ import annotations

import dataclasses

from ai_knot._canonical_enrichment import enrich_canonical_surface
from ai_knot._purpose_lexicon import STEM_TO_PURPOSE
from ai_knot._routine_lexicon import STEM_TO_ROUTINE
from ai_knot._visual_object_lexicon import STEM_TO_OBJECT
from ai_knot.types import Fact


def _fact(content: str, canonical_surface: str = "") -> Fact:
    return dataclasses.replace(Fact(content=content), canonical_surface=canonical_surface)


class TestPurposeLexicon:
    def test_mentor_maps_to_mentoring(self) -> None:
        assert "mentoring" in STEM_TO_PURPOSE["mentor"]

    def test_child_maps_to_children(self) -> None:
        assert "children" in STEM_TO_PURPOSE[" child"]

    def test_no_proper_nouns(self) -> None:
        for stem in STEM_TO_PURPOSE:
            assert stem == stem.lower(), f"stem {stem!r} contains uppercase"


class TestVisualObjectLexicon:
    def test_bowl_maps_to_bowl(self) -> None:
        assert STEM_TO_OBJECT["bowl"] == "bowl"

    def test_cup_maps_to_cup(self) -> None:
        assert STEM_TO_OBJECT[" cup"] == "cup"

    def test_no_proper_nouns(self) -> None:
        for stem in STEM_TO_OBJECT:
            assert stem == stem.lower(), f"stem {stem!r} contains uppercase"


class TestRoutineLexicon:
    def test_roast_maps_to_roasting(self) -> None:
        assert STEM_TO_ROUTINE["roast"] == "roasting"

    def test_marshmallow_maps_to_roasting(self) -> None:
        assert STEM_TO_ROUTINE["marshmallow"] == "roasting"

    def test_story_maps_to_storytelling(self) -> None:
        assert STEM_TO_ROUTINE["story"] == "storytelling"

    def test_no_proper_nouns(self) -> None:
        for stem in STEM_TO_ROUTINE:
            assert stem == stem.lower(), f"stem {stem!r} contains uppercase"


class TestEnrichCanonicalSurface:
    def test_mentoring_content_enriched(self) -> None:
        f = _fact("Caroline tutored children at the school speech event")
        enrich_canonical_surface(f)
        assert "mentoring" in f.canonical_surface or "teaching" in f.canonical_surface

    def test_pottery_objects_enriched(self) -> None:
        f = _fact("Melanie made a bowl and a cup during pottery class")
        enrich_canonical_surface(f)
        assert "bowl" in f.canonical_surface or "cup" in f.canonical_surface

    def test_camping_routine_enriched(self) -> None:
        f = _fact("They roast marshmallows and tell stories on the hike")
        enrich_canonical_surface(f)
        assert "roasting" in f.canonical_surface
        assert "storytelling" in f.canonical_surface

    def test_empty_content_no_change(self) -> None:
        f = _fact("")
        enrich_canonical_surface(f)
        assert f.canonical_surface == ""

    def test_no_match_leaves_surface_unchanged(self) -> None:
        f = _fact("The weather was pleasant today")
        enrich_canonical_surface(f)
        assert f.canonical_surface == ""

    def test_existing_canonical_surface_preserved(self) -> None:
        f = _fact("She mentors youth", canonical_surface="existing terms")
        enrich_canonical_surface(f)
        assert f.canonical_surface.startswith("existing terms")
        assert "mentoring" in f.canonical_surface
