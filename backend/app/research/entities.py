"""Entity resolution: many ways of naming one instrument, one canonical answer.

Research pulls from sources that each spell a company differently, so every symbol entering the system passes
through here. Resolution is exact-match first and never guesses between two equally good candidates.
"""

from __future__ import annotations

import re

from app.models.instrument import Instrument
from app.repositories.instrument_repository import InstrumentRepository

# Ticker suffixes used by data vendors and portals for the same NSE or BSE listing.
SUFFIXES = (".NS", ".NSE", ".BO", ".BSE", ":NSE", ":BSE", "-EQ", ".EQ")
ISIN = re.compile(r"^IN[A-Z0-9]{10}$")
_CLEAN = re.compile(r"[^A-Z0-9&-]")


def normalise(raw: str) -> str:
    """Upper-case, strip whitespace and drop a vendor suffix. `reliance.ns` becomes `RELIANCE`."""
    value = _CLEAN.sub("", raw.strip().upper().replace(" ", ""))
    upper = raw.strip().upper()
    for suffix in SUFFIXES:
        if upper.endswith(suffix):
            return _CLEAN.sub("", upper[: -len(suffix)])
    return value


def looks_like_isin(raw: str) -> bool:
    return bool(ISIN.match(raw.strip().upper()))


class InstrumentResolver:
    """Resolves a symbol, ticker, ISIN or exchange token to the one instrument it means."""

    def __init__(self, instruments: InstrumentRepository) -> None:
        self.instruments = instruments

    async def resolve(self, raw: str, exchange: str = "NSE") -> Instrument | None:
        text = raw.strip()
        if not text:
            return None
        exchange = exchange.strip().upper() or "NSE"

        if looks_like_isin(text):
            matches = await self.instruments.find_by_isin(text.upper())
            return matches[0] if len(matches) == 1 else None

        exact = await self.instruments.get_by_symbol(text.upper(), exchange)
        if exact is not None:
            return exact
        cleaned = normalise(text)
        if cleaned and cleaned != text.upper():
            suffixed = await self.instruments.get_by_symbol(cleaned, exchange)
            if suffixed is not None:
                return suffixed
        if text.isdigit():
            by_token = await self.instruments.find_by_token(text, exchange)
            if len(by_token) == 1:
                return by_token[0]
        # A name is only accepted when exactly one instrument matches it, so an ambiguous name resolves to nothing.
        by_name = await self.instruments.find_by_name(text)
        return by_name[0] if len(by_name) == 1 else None
