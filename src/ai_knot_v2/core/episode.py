"""RawEpisode — immutable raw conversation turn."""

from __future__ import annotations

import dataclasses
from typing import Any, Literal


@dataclasses.dataclass(frozen=True, slots=True)
class RawEpisode:
    episode_id: str
    agent_id: str
    user_id: str | None
    session_id: str
    turn_index: int
    speaker: Literal["user", "agent", "system"]
    text: str
    timestamp: int  # epoch-seconds
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict, hash=False)
