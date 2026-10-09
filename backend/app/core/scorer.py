from .models import Reason, Signal

SPECS = {
    "video_velocity": (
        "Video velocity",
        "hype",
        0.30,
        "clamp(100 × log₂((V30 + 1) / (B + 1)) / 3); B = V31–90 / 2",
    ),
    "search_spike": (
        "Search spike",
        "hype",
        0.25,
        "clamp(100 × (R − 1) / 4); R = last 4 weeks mean / prior 48 weeks median",
    ),
    "tip_density": ("Tip-group density", "hype", 0.20, "min(100, 20 × matching indexed tip-group pages)"),
    "paid_promotion": (
        "Paid promotion",
        "hype",
        0.15,
        "min(100, 35 × relevant ad creatives in the last 90 days)",
    ),
    "price_volume": (
        "Price-volume anomaly",
        "hype",
        0.10,
        "100 if return > 40% and volume > 3×; 50 if one holds; otherwise 0",
    ),
    "news_coverage": (
        "News coverage",
        "support",
        0.40,
        "min(100, 25 × distinct recognised outlets in the last 30 days)",
    ),
    "financial_trend": (
        "Financial trend",
        "support",
        0.35,
        "100 if four-quarter revenue trend and aggregate net income are positive; 50 if one; 0 if neither",
    ),
    "registered_promoters": (
        "Registered promoters",
        "support",
        0.25,
        "100 × share of distinct promoters with an exact or normalized registry match; at least 2 promoters",
    ),
}


def signal(
    name: str,
    window: str,
    *,
    score: float | None = None,
    value: float | None = None,
    unit: str = "",
    explanation: str = "No usable data returned.",
    inputs=None,
    evidence=None,
    calls=None,
):
    label, side, weight, rule = SPECS[name]
    has_data = score is not None and bool(evidence)
    return Signal(
        name=name,
        label=label,
        side=side,
        weight=weight,
        rule=rule,
        window=window,
        score=round(max(0, min(100, score)), 2) if has_data else None,
        value=value if has_data else None,
        unit=unit,
        has_data=has_data,
        explanation=explanation,
        inputs=inputs or {},
        evidence=evidence or [],
        call_ids=calls or [],
    )


def weighted_mean(signals: list[Signal], side: str) -> float | None:
    available = [s for s in signals if s.side == side and s.has_data and s.score is not None]
    if not available:
        return None
    return round(sum(s.weight * s.score for s in available) / sum(s.weight for s in available), 2)


def score_run(signals: list[Signal]):
    hype, support = weighted_mean(signals, "hype"), weighted_mean(signals, "support")
    available = [s for s in signals if s.side == "hype" and s.has_data]
    # Missing support is unknown; treating it as zero would manufacture a high-risk verdict.
    if len(available) < 3 or hype is None or support is None:
        verdict = "Insufficient data"
    elif hype >= 60 and support <= 40:
        verdict = "High"
    elif (hype >= 40 and hype - support >= 20) or (any(s.score == 100 for s in available) and support < 50):
        verdict = "Elevated"
    else:
        verdict = "Low"
    reasons = [
        Reason(
            signal_name=s.name, title=s.label, explanation=s.explanation, score=s.score, evidence=s.evidence
        )
        for s in sorted(available, key=lambda s: s.score, reverse=True)[:3]
    ]
    return hype, support, verdict, reasons
