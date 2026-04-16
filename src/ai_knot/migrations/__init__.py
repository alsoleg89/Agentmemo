"""Database schema migrations for ai_knot."""

from __future__ import annotations

from ai_knot.migrations.v2_query_planes import apply_v2_migration
from ai_knot.migrations.v3_plane_embeddings import apply_v3_migration

__all__ = ["apply_v2_migration", "apply_v3_migration"]
