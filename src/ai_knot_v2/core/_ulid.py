"""Minimal ULID generator — no external dependencies."""

from __future__ import annotations

import secrets
import struct
import time

_ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford Base32


def new_ulid() -> str:
    """Return a 26-char Crockford Base32 ULID (time-ordered, millisecond precision)."""
    ts_ms = int(time.time() * 1000)
    ts_bytes = struct.pack(">Q", ts_ms)[-6:]  # 48-bit timestamp
    rand_bytes = secrets.token_bytes(10)
    raw = ts_bytes + rand_bytes  # 16 bytes = 128 bits
    n = int.from_bytes(raw, "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(_ENCODING[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))
