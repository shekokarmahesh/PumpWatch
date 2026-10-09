import asyncio
import time
from datetime import datetime, timezone
from uuid import uuid4

from .cache import Cache
from .collectors import ads, finance, news, search, trends, youtube
from .collectors.base import Context
from .config import DISCLAIMER, Settings
from .models import Analysis, SnapshotResponse
from .registry import Registry
from .resolver import Resolver
from .scorer import SPECS, score_run, signal
from .store import Store, utcnow


class Service:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Store(settings.state_dir / "pumpwatch.sqlite")
        self.cache = Cache(settings, self.store)
        self.resolver = Resolver(self.cache)
        self.snapshot_lock = asyncio.Lock()

    async def analyse(self, symbol: str, exchange: str, snapshot: bool = False) -> Analysis:
        deadline = time.monotonic() + 27
        ticker = await self.resolver.get(symbol, exchange)
        previous = self.store.latest(ticker.key)
        as_of = (
            datetime.fromisoformat(self.cache.manifest["as_of"])
            if self.settings.mode == "replay"
            else datetime.now(timezone.utc)
        )
        ctx = Context(ticker, self.cache, uuid4().hex, as_of, deadline, snapshot, previous)
        modules = [finance, youtube, trends] if snapshot else [finance, youtube, trends, search, news, ads]
        collected = await asyncio.gather(*(m.collect(ctx) for m in modules), return_exceptions=True)
        signals = [s for result in collected if isinstance(result, list) for s in result]
        warnings = [
            f"{module.__name__.rsplit('.', 1)[-1]}: Response parsing failed; affected signals are unavailable."
            for module, output in zip(modules, collected)
            if isinstance(output, Exception)
        ]
        if snapshot and previous:
            present = {s.name for s in signals if s.has_data}
            for prior in previous.signals:
                if prior.name not in present and prior.has_data:
                    carried = prior.model_copy(deep=True)
                    carried.carried = True
                    carried.explanation += " Carried from the previous run; not a fresh observation."
                    signals = [s for s in signals if s.name != prior.name] + [carried]
        for name in SPECS:
            if name not in {s.name for s in signals}:
                signals.append(
                    signal(name, "Unavailable", explanation="Signal was not collected or collection failed.")
                )
        registry = Registry(self.settings.data_dir, ticker.synthetic)
        promoter_evidence = [
            e
            for s in signals
            if s.name in {"video_velocity", "paid_promotion"}
            for e in s.evidence
            if e.promoter_name
        ]
        names = sorted(set(e.promoter_name for e in promoter_evidence))
        matches = {name: registry.match(name, allow_not_found=len(names) >= 2) for name in names}
        for ev in promoter_evidence:
            ev.promoter = matches[ev.promoter_name]
        registered = sum(p.status == "registered" for p in matches.values())
        promoter_score = 100 * registered / len(names) if len(names) >= 2 and registry.ready else None
        signals = [s for s in signals if s.name != "registered_promoters"] + [
            signal(
                "registered_promoters",
                "Distinct promoters in this result",
                score=promoter_score,
                value=promoter_score,
                unit="% matched",
                explanation=f"{registered} of {len(names)} promoter names match the imported registry."
                if registry.ready
                else "A current verified registry has not been imported. Promoter registration is not checked.",
                inputs={
                    "registered": registered,
                    "distinct_promoters": len(names),
                    "registry_synthetic": ticker.synthetic,
                },
                evidence=promoter_evidence,
                calls=[
                    c.id
                    for c in self.store.calls(ctx.run_id)
                    if c.engine in {"youtube", "google_ads_transparency_center"}
                ],
            )
        ]
        signals.sort(key=lambda s: list(SPECS).index(s.name))
        hype, support, verdict, reasons = score_run(signals)
        calls = self.store.calls(ctx.run_id)
        warnings.extend(f"{c.engine}: {c.error}" for c in calls if c.status != "success")
        if ticker.synthetic:
            warnings.append(
                "Fictional demo scenario. All observations, registry entries and evidence URLs are synthetic."
            )
        elif not registry.ready:
            warnings.append("SEBI registry unavailable or stale; promoter registration is not checked.")
        if support is None:
            warnings.append("Support is unknown; an attention-risk verdict cannot be justified.")
        if snapshot:
            warnings.append(
                "Snapshot uses three requests; carried signals and baselines are explicitly marked."
            )
        dates = [c.fetched_at for c in calls if c.status == "success"]
        result = Analysis(
            run_id=ctx.run_id,
            ticker=ticker,
            run_at=utcnow(),
            data_as_of=min(dates) if dates else as_of.isoformat(),
            mode=self.settings.mode,
            synthetic=ticker.synthetic,
            hype_score=hype,
            support_score=support,
            verdict=verdict,
            signals_available=sum(s.has_data for s in signals if s.side == "hype"),
            support_available=sum(s.has_data for s in signals if s.side == "support"),
            reasons=reasons,
            signals=signals,
            promoters=list(matches.values()),
            warnings=warnings,
            disclaimer=DISCLAIMER,
            snapshot=snapshot,
        )
        self.store.save(result)
        return result

    async def snapshot(self, symbol: str | None = None, exchange: str = "NSE") -> SnapshotResponse:
        async with self.snapshot_lock:
            tickers = (
                [await self.resolver.get(symbol, exchange)]
                if symbol
                else [item.ticker for item in self.store.watchlist()]
            )
            runs, skipped = [], 0
            for ticker in tickers:
                if self.store.today_snapshot(ticker.key, self.settings.mode):
                    skipped += 1
                    continue
                result = await self.analyse(ticker.symbol, ticker.exchange, snapshot=True)
                runs.append(result.run_id)
            return SnapshotResponse(rows_written=len(runs), run_ids=runs, skipped=skipped)
