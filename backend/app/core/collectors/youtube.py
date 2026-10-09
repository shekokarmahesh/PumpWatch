import asyncio
import math

from ..normalize import dedupe, evidence, has_keyword, names_stock, parsed_date
from ..scorer import signal
from .base import Context

# YouTube protobuf filters: upload this month / this year. Dates are checked again locally.
MONTH_FILTER = "EgIIBA=="
YEAR_FILTER = "EgIIBQ=="


def parameters(name: str, window: str):
    return {
        "engine": "youtube",
        "search_query": f"{name} target",
        "sp": MONTH_FILTER if window == "month" else YEAR_FILTER,
    }


async def collect(ctx: Context):
    month_task = ctx.fetch(**parameters(ctx.ticker.company_name, "month"))
    if ctx.snapshot:
        month, month_call = await month_task
        year, year_call = {}, None
    else:
        (month, month_call), (year, year_call) = await asyncio.gather(
            month_task, ctx.fetch(**parameters(ctx.ticker.company_name, "year"))
        )
    calls = [month_call.id] + ([year_call.id] if year_call else [])
    seen, recent, old, observed = set(), [], [], []
    dated_count = 0
    for raw in [month, year]:
        reference = ctx.reference_date(raw)
        for row in raw.get("video_results", []):
            url = row.get("link")
            if not url or url in seen:
                continue
            seen.add(url)
            dt = parsed_date(row.get("published_date"), reference)
            ev = evidence(
                url,
                row.get("title", "Video"),
                "YouTube",
                dt,
                row.get("channel", {}).get("name"),
                ctx.ticker.synthetic,
            )
            if ev is None:
                continue
            observed.append(ev)
            if not dt:
                continue
            dated_count += 1
            age = (reference - dt).total_seconds() / 86400
            if names_stock(ev.title, ctx.ticker) and has_keyword(ev.title):
                if 0 <= age <= 30:
                    recent.append(ev)
                elif 30 < age <= 90:
                    old.append(ev)
    prior = ctx.prior("video_velocity")
    baseline = (
        len(old) / 2
        if year_call and year_call.status == "success" and year.get("video_results")
        else (prior.inputs.get("baseline_monthly_videos") if ctx.snapshot and prior else None)
    )
    ratio = (len(recent) + 1) / (baseline + 1) if baseline is not None else None
    score = 100 * math.log2(ratio) / 3 if ratio is not None and observed and dated_count else None
    result = signal(
        "video_velocity",
        "Last 30 days vs days 31–90",
        score=score,
        value=ratio,
        unit="× velocity",
        explanation=f"{len(recent)} matching videos in 30 days, versus {baseline:g} per month in the baseline."
        if baseline is not None
        else "A dated video sample and a comparable baseline are required.",
        inputs={
            "recent_videos": len(recent),
            "baseline_videos_60_days": len(old) if year_call else None,
            "baseline_monthly_videos": baseline,
            "velocity_ratio_smoothed": ratio,
            "sample_size": len(observed),
            "sampling_note": "Counts are from the returned search sample, not all YouTube uploads; relative months use 30 days.",
        },
        evidence=dedupe(recent + old) or observed[:3],
        calls=calls,
    )
    if ctx.snapshot and prior:
        result.carried = True
        result.explanation += " Historical baseline carried from the previous analysis."
    return [result]
