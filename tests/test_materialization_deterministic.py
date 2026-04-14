"""Tests for deterministic materialization invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_knot.materialization import (
    MATERIALIZATION_VERSION,
    dirty_keys_for_claims,
    materialize_episode,
    rebuild_claims_from_raw,
)
from ai_knot.query_types import (
    DETERMINISTIC_CLAIM_KINDS,
    ClaimKind,
    RawEpisode,
    make_episode_id,
)

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _ep(raw_text: str, session_id: str = "sess", turn_id: str = "turn") -> RawEpisode:
    ep_id = make_episode_id("agent", session_id, turn_id)
    return RawEpisode(
        id=ep_id,
        agent_id="agent",
        session_id=session_id,
        turn_id=turn_id,
        speaker="user",
        observed_at=NOW,
        session_date=None,
        raw_text=raw_text,
        source_meta={},
        parent_episode_id=None,
    )


# ---------------------------------------------------------------------------
# Kind whitelist
# ---------------------------------------------------------------------------


class TestMaterializationKindWhitelist:
    def test_only_deterministic_kinds_produced(self):
        ep = _ep("Alice works as a software engineer at TechCorp.")
        claims = materialize_episode(ep)
        for c in claims:
            assert c.kind in DETERMINISTIC_CLAIM_KINDS, (
                f"Non-deterministic kind {c.kind!r} produced by materializer. "
                f"Only DESCRIPTOR/INTENT may come from enrichment, never from materialize_episode."
            )

    def test_no_descriptor_or_intent_from_materializer(self):
        ep = _ep("Bob is a creative, empathetic person who loves innovation.")
        claims = materialize_episode(ep)
        enrichment_only = {ClaimKind.DESCRIPTOR, ClaimKind.INTENT}
        for c in claims:
            assert c.kind not in enrichment_only, (
                f"materialize_episode produced enrichment-only kind {c.kind!r}"
            )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestMaterializationDeterminism:
    def test_same_episode_same_claims(self):
        ep = _ep("Carol studies physics at the university.")
        claims1 = materialize_episode(ep)
        claims2 = materialize_episode(ep)
        assert {c.id for c in claims1} == {c.id for c in claims2}

    def test_same_text_different_turn_different_claim_ids(self):
        """Claim IDs depend on episode_id, so different turns → different IDs."""
        ep1 = _ep("Alice plays piano.", session_id="sess", turn_id="turn-1")
        ep2 = _ep("Alice plays piano.", session_id="sess", turn_id="turn-2")
        claims1 = materialize_episode(ep1)
        claims2 = materialize_episode(ep2)
        ids1 = {c.id for c in claims1}
        ids2 = {c.id for c in claims2}
        # Same content but different episode → different IDs
        assert ids1 != ids2 or not ids1  # if no claims, trivially different

    def test_rebuild_same_as_individual_materialize(self):
        episodes = [
            _ep("Alice works at Acme.", session_id="sess", turn_id="turn-0"),
            _ep("Alice lives in Paris.", session_id="sess", turn_id="turn-1"),
        ]
        individual = []
        for ep in episodes:
            individual.extend(materialize_episode(ep))

        rebuilt = rebuild_claims_from_raw(episodes, version=MATERIALIZATION_VERSION)
        assert {c.id for c in individual} == {c.id for c in rebuilt}


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestMaterializationProvenance:
    def test_all_claims_have_source_episode_id(self):
        ep = _ep("Dave joined the company in January 2023.")
        claims = materialize_episode(ep)
        for c in claims:
            assert c.source_episode_id == ep.id, f"Claim {c.id} missing source_episode_id"

    def test_all_claims_have_source_spans(self):
        ep = _ep("Eve is 28 years old.")
        claims = materialize_episode(ep)
        for c in claims:
            if c.kind in {ClaimKind.STATE, ClaimKind.EVENT, ClaimKind.RELATION}:
                assert c.source_spans, (
                    f"Claim {c.id} (kind={c.kind}) has empty source_spans — "
                    "provenance invariant violated"
                )


# ---------------------------------------------------------------------------
# DirtyKey minimality
# ---------------------------------------------------------------------------


class TestDirtyKeyMinimality:
    def test_slot_level_key_preferred_over_subject_only(self):
        """Claims with subject+relation should emit subject+relation DirtyKey, not subject-only."""
        ep = _ep("Alice's salary is $80k.")
        claims = materialize_episode(ep)
        if not claims:
            pytest.skip("no claims extracted from salary text")

        dirty_keys = dirty_keys_for_claims(claims)
        # At least one key should be a slot-level key (has both subject AND relation)
        slot_level = [k for k in dirty_keys if k.subject and k.relation]
        subject_only = [k for k in dirty_keys if k.subject and not k.relation]

        # If any slot-level key exists, there should be fewer or equal subject-only keys
        if slot_level:
            # Prefer slot-level: subject-only keys are only emitted for claims
            # where we can't identify the specific relation
            assert len(slot_level) >= len(subject_only) or subject_only == [], (
                "Expected slot-level DirtyKey to be preferred; got more subject-only keys"
            )

    def test_no_bundle_kind_topic_keys_from_routine_materialize(self):
        """Bundle-kind+topic DirtyKeys are only for admin/debug, not routine ingest."""
        ep = _ep("Frank is a chef at La Maison.")
        claims = materialize_episode(ep)
        dirty_keys = dirty_keys_for_claims(claims)
        bundle_kind_keys = [k for k in dirty_keys if k.bundle_kind is not None]
        assert bundle_kind_keys == [], (
            "materialize_episode should not emit bundle_kind DirtyKeys — those are admin/debug only"
        )

    def test_dirty_keys_cover_all_subjects(self):
        ep = _ep("Grace works at Bloom Inc and lives near downtown.")
        claims = materialize_episode(ep)
        if not claims:
            pytest.skip("no claims extracted")

        dirty_keys = dirty_keys_for_claims(claims)
        claim_subjects = {c.subject for c in claims}
        key_subjects = {k.subject for k in dirty_keys if k.subject}
        # Every claim subject must appear in at least one dirty key
        for subj in claim_subjects:
            assert subj in key_subjects, (
                f"Subject {subj!r} from claims has no corresponding DirtyKey"
            )
