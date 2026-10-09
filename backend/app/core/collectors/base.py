from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..cache import Cache
from ..models import Analysis, Ticker


@dataclass
class Context:
    ticker: Ticker
    cache: Cache
    run_id: str
    as_of: datetime
    deadline: float
    snapshot: bool = False
    previous: Analysis | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    async def fetch(self, **params):
        raw, call = await self.cache.fetch(params, self.run_id, self.deadline)
        self.raw[call.id] = raw
        return raw, call

    def reference_date(self, raw):
        from ..normalize import parsed_date

        return parsed_date(raw.get("_pumpwatch_fetched_at"), self.as_of) or self.as_of

    def prior(self, name):
        return (
            next((s for s in self.previous.signals if s.name == name and s.has_data), None)
            if self.previous
            else None
        )
