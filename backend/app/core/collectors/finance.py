import asyncio
import statistics
from collections import defaultdict
from datetime import timedelta

from ..normalize import evidence, number, parsed_date
from ..scorer import signal
from .base import Context


def parameters(key: str, window: str):
    return {"engine": "google_finance", "q": key, "window": window, "hl": "en"}


def daily_graph(raw, as_of):
    days = defaultdict(lambda: {"volume": 0, "has_volume": False, "prices": []})
    for point in raw.get("graph", []):
        dt = parsed_date(point.get("date"), as_of)
        if not dt:
            continue
        day = days[dt.date().isoformat()]
        price, volume = number(point.get("price")), number(point.get("volume"))
        if price is not None:
            day["prices"].append((dt, price))
        if volume is not None:
            day["volume"] += volume
            day["has_volume"] = True
    prices = [price for day in sorted(days) for _, price in sorted(days[day]["prices"])]
    volumes = [day["volume"] for day in days.values() if day["has_volume"]]
    return prices, volumes


async def collect(ctx: Context):
    month_task = ctx.fetch(**parameters(ctx.ticker.key, "1M"))
    if ctx.snapshot:
        month, month_call = await month_task
        year, year_call = {}, None
    else:
        (month, month_call), (year, year_call) = await asyncio.gather(
            month_task, ctx.fetch(**parameters(ctx.ticker.key, "1Y"))
        )
    calls = [month_call.id] + ([year_call.id] if year_call else [])
    url = (
        month.get("search_metadata", {}).get("google_finance_url")
        or f"https://www.google.com/finance/quote/{ctx.ticker.key}"
    )
    ev = evidence(
        url,
        f"{ctx.ticker.company_name} · price history and financial statements",
        "Google Finance",
        synthetic=ctx.ticker.synthetic,
    )
    prices, volumes = daily_graph(month, ctx.reference_date(month))
    _, baseline_volumes = daily_graph(year, ctx.reference_date(year))
    baseline_dates = {
        dt.date()
        for point in year.get("graph", [])
        if (dt := parsed_date(point.get("date"), ctx.reference_date(year)))
        and number(point.get("volume")) is not None
        and dt < ctx.reference_date(year) - timedelta(days=30)
    }
    prior = ctx.prior("price_volume")
    baseline = (
        statistics.mean(baseline_volumes)
        if baseline_volumes and baseline_dates
        else (prior.inputs.get("year_average_volume") if ctx.snapshot and prior else None)
    )
    ret = (prices[-1] / prices[0] - 1) * 100 if len(prices) >= 2 and prices[0] > 0 else None
    avg = statistics.mean(volumes) if volumes else None
    ratio = avg / baseline if avg is not None and baseline and baseline > 0 else None
    score = (50 * int(ret > 40) + 50 * int(ratio > 3)) if ret is not None and ratio is not None else None
    price_signal = signal(
        "price_volume",
        "Last 30 days vs one-year daily volume",
        score=score,
        value=ret,
        unit="% return",
        explanation=f"Price moved {ret:+.1f}% with {ratio:.1f}× average daily volume."
        if score is not None
        else f"Comparable historical volume is unavailable. The recent sample has {len(volumes)} trading days; a baseline older than the last 30 days is required.",
        inputs={
            "month_return_percent": ret,
            "month_average_volume": avg,
            "year_average_volume": baseline,
            "volume_ratio": ratio,
            "sampled_days": len(volumes),
            "baseline_sampled_days": len(baseline_volumes),
            "baseline_days_older_than_30": len(baseline_dates),
        },
        evidence=[ev] if ev and month else [],
        calls=calls,
    )
    if ctx.snapshot and prior and not baseline_volumes:
        price_signal.carried = True
        price_signal.explanation += " One-year volume baseline carried from the previous analysis."
    financials = month.get("financials") or year.get("financials") or []
    quarters = []
    for statement in financials:
        if statement.get("title", "").casefold() != "income statement":
            continue
        for period in statement.get("results", []):
            if period.get("period_type", "").casefold() != "quarterly":
                continue
            dt = parsed_date(period.get("date"), ctx.as_of)
            values = {
                row.get("title", "").casefold(): number(row.get("value")) for row in period.get("table", [])
            }
            if dt and values.get("revenue") is not None and values.get("net income") is not None:
                quarters.append((dt, values["revenue"], values["net income"]))
    quarters = sorted({q[0]: q for q in quarters}.values())[-4:]
    revenue_growth = quarters[-1][1] - quarters[0][1] if len(quarters) == 4 else None
    net_income = sum(q[2] for q in quarters) if len(quarters) == 4 else None
    financial_score = (
        (50 * int(revenue_growth > 0) + 50 * int(net_income > 0)) if revenue_growth is not None else None
    )
    financial_signal = signal(
        "financial_trend",
        "Last four reported quarters",
        score=financial_score,
        value=financial_score,
        unit="/100",
        explanation=(
            f"Revenue trend is {'positive' if revenue_growth > 0 else 'non-positive'}; aggregate net income is "
            f"{'positive' if net_income > 0 else 'non-positive'}."
            if revenue_growth is not None
            else "Four complete quarterly income statements are unavailable."
        ),
        inputs={
            "revenue_change": revenue_growth,
            "aggregate_net_income": net_income,
            "quarters": [
                {"date": q[0].date().isoformat(), "revenue": q[1], "net_income": q[2]} for q in quarters
            ],
        },
        evidence=[ev] if ev and financials else [],
        calls=calls,
    )
    return [price_signal, financial_signal]
