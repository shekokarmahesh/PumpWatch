from urllib.parse import urlparse

from ..normalize import dedupe, evidence, has_keyword, names_stock, parsed_date
from ..scorer import signal
from .base import Context


def parameters(name: str):
    return {
        "engine": "google",
        "q": f'"{name}" (target OR multibagger OR "buy call") (site:t.me OR site:whatsapp.com OR site:chat.whatsapp.com)',
        "gl": "in",
        "hl": "en",
        "tbs": "qdr:m",
    }


async def collect(ctx: Context):
    raw, call = await ctx.fetch(**parameters(ctx.ticker.company_name))
    rows, matched, observed = raw.get("organic_results", []), [], []
    for row in rows:
        dt = parsed_date(row.get("date"), ctx.reference_date(raw))
        ev = evidence(
            row.get("link"),
            row.get("title", "Indexed group page"),
            "Google Search",
            dt,
            synthetic=ctx.ticker.synthetic,
        )
        if not ev:
            continue
        observed.append(ev)
        host = urlparse(ev.url).hostname or ""
        text = ev.title + " " + row.get("snippet", "")
        if (
            host in {"t.me", "whatsapp.com", "www.whatsapp.com", "chat.whatsapp.com"}
            and has_keyword(text)
            and names_stock(text, ctx.ticker)
        ):
            if dt is None or 0 <= (ctx.reference_date(raw) - dt).days <= 30:
                matched.append(ev)
    matched = dedupe(matched)
    return [
        signal(
            "tip_density",
            "Indexed pages · past month",
            score=20 * len(matched) if observed else None,
            value=len(matched),
            unit="pages",
            explanation=f"{len(matched)} indexed tip-group pages name this stock and use promotional keywords.",
            inputs={
                "matching_pages": len(matched),
                "sample_size": len(rows),
                "date_filter": "qdr:m; undated items rely on Google's filter",
            },
            evidence=matched or observed[:3],
            calls=[call.id],
        )
    ]
