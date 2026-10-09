from ..normalize import dedupe, evidence, names_stock, parsed_date
from ..scorer import signal
from .base import Context


def parameters(name: str):
    return {"engine": "google_ads_transparency_center", "text": name, "region": "2356"}


async def collect(ctx: Context):
    raw, call = await ctx.fetch(**parameters(ctx.ticker.company_name))
    matched, observed = [], []
    for row in raw.get("ad_creatives", []):
        dt = parsed_date(row.get("last_shown"), ctx.reference_date(raw))
        advertiser = row.get("advertiser", "Unknown advertiser")
        if isinstance(advertiser, dict):
            advertiser = advertiser.get("name", "Unknown advertiser")
        title = row.get("title") or f"{advertiser} · {row.get('format', 'ad')} creative"
        ev = evidence(
            row.get("details_link") or row.get("link"),
            title,
            "Ads Transparency Center",
            dt,
            advertiser,
            ctx.ticker.synthetic,
        )
        if not ev:
            continue
        observed.append(ev)
        # A returned ad is not attributable to this stock just because the search returned it.
        attributable = names_stock(title + " " + advertiser + " " + row.get("text", ""), ctx.ticker)
        if attributable and dt and 0 <= (ctx.reference_date(raw) - dt).days <= 90:
            matched.append(ev)
    matched = dedupe(matched)
    return [
        signal(
            "paid_promotion",
            "Relevant creatives · last 90 days",
            score=35 * len(matched) if observed else None,
            value=len(matched),
            unit="creatives",
            explanation=f"{len(matched)} recent ad creatives can be attributed to this stock.",
            inputs={
                "relevant_creatives": len(matched),
                "sample_size": len(observed),
                "note": "Association is checked in returned text/advertiser names; it does not establish a stock recommendation.",
            },
            evidence=matched or observed[:3],
            calls=[call.id],
        )
    ]
