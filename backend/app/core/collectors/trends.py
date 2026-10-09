import statistics
from urllib.parse import urlencode

from ..normalize import evidence, number
from ..scorer import signal
from .base import Context


def parameters(name: str):
    return {
        "engine": "google_trends",
        "q": name,
        "geo": "IN",
        "data_type": "TIMESERIES",
        "date": "today 12-m",
    }


async def collect(ctx: Context):
    raw, call = await ctx.fetch(**parameters(ctx.ticker.company_name))
    timeline = raw.get("interest_over_time", {}).get("timeline_data", [])
    # Do not turn missing values or the still-incomplete current week into zeros.
    values = []
    for row in timeline:
        if row.get("partial_data") or row.get("is_partial"):
            continue
        cell = (row.get("values") or [{}])[0]
        value = number(cell.get("extracted_value", cell.get("value")))
        if value is not None:
            values.append(value)
    ratio, baseline, recent = None, None, None
    if len(values) >= 52:
        baseline, recent = statistics.median(values[-52:-4]), statistics.mean(values[-4:])
        if baseline > 0:
            ratio = recent / baseline
    url = "https://trends.google.com/trends/explore?" + urlencode(
        {"q": ctx.ticker.company_name, "geo": "IN", "date": "today 12-m"}
    )
    ev = evidence(
        url,
        f"{ctx.ticker.company_name} · India search interest",
        "Google Trends",
        synthetic=ctx.ticker.synthetic,
    )
    return [
        signal(
            "search_spike",
            "Last 4 complete weeks vs prior 48 weeks · India",
            score=100 * (ratio - 1) / 4 if ratio is not None else None,
            value=ratio,
            unit="× search interest",
            explanation=f"Search interest is {ratio:.1f}× its 48-week median."
            if ratio is not None
            else "52 complete weekly values and a non-zero baseline are required.",
            inputs={"recent_mean": recent, "baseline_median": baseline, "complete_weeks": len(values)},
            evidence=[ev] if ev and values else [],
            calls=[call.id],
        )
    ]
