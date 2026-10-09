from urllib.parse import urlparse

from ..normalize import dedupe, evidence, names_stock, parsed_date
from ..scorer import signal
from .base import Context


def parameters(name: str):
    return {"engine": "google_news", "q": name, "gl": "in", "hl": "en"}


async def collect(ctx: Context):
    raw, call = await ctx.fetch(**parameters(ctx.ticker.company_name))
    outlets = set((ctx.cache.settings.data_dir / "outlets.txt").read_text().splitlines())
    matched, observed, sources = [], [], set()

    def flatten(rows):
        for row in rows:
            if row.get("stories"):
                yield from flatten(row["stories"])
            else:
                yield row

    for row in flatten(raw.get("news_results", [])):
        source = row.get("source", {})
        source_name = source.get("name", "Unknown outlet") if isinstance(source, dict) else str(source)
        dt = parsed_date(row.get("iso_date") or row.get("date"), ctx.reference_date(raw))
        ev = evidence(
            row.get("link"), row.get("title", "News item"), source_name, dt, synthetic=ctx.ticker.synthetic
        )
        if not ev:
            continue
        observed.append(ev)
        source_url = source.get("url", ev.url) if isinstance(source, dict) else ev.url
        host = (urlparse(source_url).hostname or "").removeprefix("www.")
        outlet = next((d for d in outlets if host == d or host.endswith("." + d)), None)
        if (
            outlet
            and dt
            and 0 <= (ctx.reference_date(raw) - dt).days <= 30
            and names_stock(ev.title, ctx.ticker)
        ):
            sources.add(outlet)
            matched.append(ev)
    return [
        signal(
            "news_coverage",
            "Distinct recognised outlets · past 30 days",
            score=25 * len(sources) if observed else None,
            value=len(sources),
            unit="outlets",
            explanation=f"{len(sources)} recognised news outlets covered this stock in the last 30 days.",
            inputs={
                "outlets": sorted(sources),
                "note": "Coverage measures visibility, not endorsement or financial quality.",
            },
            evidence=dedupe(matched) or observed[:3],
            calls=[call.id],
        )
    ]
