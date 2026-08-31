"""
Rotating API key pool.
 
Lets you register multiple API keys per provider (e.g. your own Groq key
plus two teammates' Groq keys) and automatically rotates to the next
available key when one gets rate-limited (HTTP 429), instead of the whole
extraction pipeline stopping.
 
Behavior:
  - Keys are tried in the order you list them (round-robin from wherever
    the pool left off), skipping any key currently in cooldown.
  - When a key returns 429, it's put in cooldown - either for however long
    the provider's `Retry-After` header says, or for `KEY_COOLDOWN_SECONDS`
    (default 60s) if no header is given.
  - If EVERY key for a provider is currently in cooldown, `acquire()`
    returns None and the caller can ask `seconds_until_next_available()`
    to find out how long until the earliest one frees up.
"""
 
from __future__ import annotations
 
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
 
from backend.config import settings
 
 
@dataclass
class ApiKeyPool:
    keys: List[str]
    cooldown_seconds: float = 60.0
    _cooldown_until: Dict[int, float] = field(default_factory=dict, init=False)
    _rr_index: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
 
    def has_keys(self) -> bool:
        return len(self.keys) > 0
 
    async def acquire(self) -> Optional[Tuple[int, str]]:
        """Return (index, key) for the next available (not-in-cooldown) key,
        advancing the round-robin cursor. Returns None if every key is
        currently in cooldown."""
        if not self.keys:
            return None
        async with self._lock:
            now = time.monotonic()
            n = len(self.keys)
            for step in range(n):
                idx = (self._rr_index + step) % n
                until = self._cooldown_until.get(idx, 0.0)
                if until <= now:
                    self._rr_index = (idx + 1) % n
                    return idx, self.keys[idx]
            return None
 
    def mark_rate_limited(self, index: int, retry_after_seconds: Optional[float] = None) -> None:
        cooldown = retry_after_seconds if retry_after_seconds and retry_after_seconds > 0 else self.cooldown_seconds
        self._cooldown_until[index] = time.monotonic() + cooldown
 
    def seconds_until_next_available(self) -> float:
        """How long until at least one key frees up. 0 if one is already free."""
        if not self.keys:
            return 0.0
        now = time.monotonic()
        soonest = min(
            (self._cooldown_until.get(i, 0.0) for i in range(len(self.keys))),
            default=now,
        )
        return max(0.0, soonest - now)
 
    def all_in_cooldown(self) -> bool:
        if not self.keys:
            return True
        now = time.monotonic()
        return all(self._cooldown_until.get(i, 0.0) > now for i in range(len(self.keys)))
 
 
def parse_retry_after(headers) -> Optional[float]:
    """Parse a Retry-After header (seconds form only - the common case for
    LLM APIs). Returns None if absent/unparseable, so the caller falls back
    to the default cooldown."""
    val = headers.get("retry-after") or headers.get("Retry-After")
    if not val:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
 
 
# ---------------------------------------------------------------------------
# One pool per provider, built once from settings at import time.
# ---------------------------------------------------------------------------
groq_key_pool = ApiKeyPool(keys=settings.groq_api_keys_list, cooldown_seconds=settings.KEY_COOLDOWN_SECONDS)
gemini_key_pool = ApiKeyPool(keys=settings.gemini_api_keys_list, cooldown_seconds=settings.KEY_COOLDOWN_SECONDS)
nvidia_key_pool = ApiKeyPool(keys=settings.nvidia_api_keys_list, cooldown_seconds=settings.KEY_COOLDOWN_SECONDS)
 
 
def get_pool(provider: str) -> ApiKeyPool:
    return {
        "groq": groq_key_pool,
        "gemini": gemini_key_pool,
        "nvidia": nvidia_key_pool,
    }[provider]
