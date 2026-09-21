"""Latest-quote cache. In-memory always; mirrored to Redis (best effort) so other processes can read it.

Ticks are never written to MySQL - this cache is the only place live prices live.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.domain.types import Quote
from app.utils.time import utcnow

logger = get_logger(__name__)
_TTL_SECONDS = 120


class QuoteCache:
    def __init__(self, redis_url: str | None = None) -> None:
        self._memory: dict[str, Quote] = {}
        self._redis = None
        if redis_url:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
                )
            except Exception:  # pragma: no cover - redis is optional
                self._redis = None

    @staticmethod
    def key(symbol: str, exchange: str) -> str:
        return f"{exchange}:{symbol}"

    async def set(self, quote: Quote) -> None:
        key = self.key(quote.symbol, quote.exchange)
        self._memory[key] = quote
        if self._redis is not None:
            try:
                payload = asdict(quote) | {"timestamp": quote.timestamp.isoformat()}
                await self._redis.set(f"quote:{key}", json.dumps(payload), ex=_TTL_SECONDS)
            except Exception:
                pass  # cache mirroring must never break trading

    async def get(self, symbol: str, exchange: str, max_age_seconds: float = 15) -> Quote | None:
        key = self.key(symbol, exchange)
        cutoff = utcnow() - timedelta(seconds=max_age_seconds)
        quote = self._memory.get(key)
        if quote is not None and quote.timestamp >= cutoff:
            return quote
        if self._redis is not None:
            try:
                raw = await self._redis.get(f"quote:{key}")
                if raw:
                    data = json.loads(raw)
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    quote = Quote(**data)
                    if quote.timestamp >= cutoff:
                        return quote
            except Exception:
                pass
        return None

    async def ping(self) -> bool | None:
        """True/False when Redis is configured, None when it is not."""
        if self._redis is None:
            return None
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
