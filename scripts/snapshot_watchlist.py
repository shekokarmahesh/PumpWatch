"""Read the configured watchlist and snapshot it; the GitHub job is opt-in."""

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.cache import write_json
from app.core.config import ROOT, Settings
from app.core.service import Service


async def main():
    service = Service(Settings())
    configured = json.loads((ROOT / "snapshots/watchlist.json").read_text())
    for key in configured:
        symbol, _, exchange = key.partition(":")
        ticker = await service.resolver.get(symbol, exchange or "NSE")
        service.store.upsert_ticker(ticker, True)
    configured_keys = set(configured)
    for item in service.store.watchlist():
        if item.ticker.key not in configured_keys:
            service.store.upsert_ticker(item.ticker, False)
    result = await service.snapshot()
    day = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    write_json(
        ROOT / "snapshots" / f"{day}.json",
        {
            "mode": service.settings.mode,
            **result.model_dump(),
            "results": [service.store.run(r).model_dump() for r in result.run_ids],
        },
    )
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
