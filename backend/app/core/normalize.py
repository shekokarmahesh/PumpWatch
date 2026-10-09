import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from .models import Evidence, Ticker

KEYWORDS = (
    "target",
    "multibagger",
    "buy",
    "breakout",
    "rocket",
    "100 percent",
    "100%",
    "kharido",
    "kharide",
    "kharid",
    "lakshya",
    "khareedo",
    "खरीद",
    "टारगेट",
    "मल्टीबैगर",
    "लक्ष्य",
)


def number(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    value = value.replace(",", "").strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*([KMBT]?)", value, re.I)
    if not match:
        return None
    scale = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[match[2].upper()]
    return float(match[1]) * scale


def parsed_date(value, as_of: datetime) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    if not value:
        return None
    value = str(value).strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" UTC", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        pass
    relative = re.search(
        r"(?<!\w)(\d+)\s*(minute|hour|day|week|month|year|min|mo|m|h|d|w|y)s?\s+ago\b", value, re.I
    )
    if relative:
        seconds = {
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31536000,
            "min": 60,
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800,
            "mo": 2592000,
            "y": 31536000,
        }[relative[2].lower()]
        return as_of - timedelta(seconds=int(relative[1]) * seconds)
    # Finance graphs include explicit UTC offsets in human-readable timestamps.
    try:
        return datetime.strptime(value, "%b %d %Y, %I:%M %p UTC%z")
    except ValueError:
        pass
    for fmt in (
        "%m/%d/%Y, %I:%M %p",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%b %Y",
        "%Y-%m-%d",
        "%b %d %Y",
        "%B %d, %Y",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def has_keyword(text: str) -> bool:
    text = text.casefold()
    return any(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", text) for k in KEYWORDS)


def company_query(name: str) -> str:
    # Finance display labels can describe the instrument, rather than the company.
    return re.sub(r"\s+(?:Ord Shs|Ordinary Shares|Ordinary Share)$", "", name, flags=re.I).strip()


def company_alias(name: str) -> str:
    name = company_query(name)
    name = re.sub(r"\s*\(India\)", "", name, flags=re.I)
    return re.sub(r"\s+(?:limited|ltd\.?|inc\.?)$", "", name, flags=re.I).strip()


def names_stock(text: str, ticker: Ticker) -> bool:
    text = re.sub(r"[^\w]+", " ", text.casefold()).strip()
    company = company_alias(ticker.company_name).casefold()
    company = re.sub(r"[^\w]+", " ", company).strip()
    return bool(company and re.search(r"\b" + re.escape(company) + r"\b", text)) or bool(
        re.search(r"\b" + re.escape(ticker.symbol.casefold()) + r"\b", text)
    )


def evidence(
    url: str | None,
    title: str,
    source: str,
    dt: datetime | None = None,
    promoter: str | None = None,
    synthetic: bool = False,
) -> Evidence | None:
    if not url or urlparse(url).scheme not in {"https", "http"}:
        return None
    return Evidence(
        url=url,
        title=title,
        source=source,
        published_at=dt.isoformat() if dt else None,
        promoter_name=promoter,
        synthetic=synthetic,
    )


def dedupe(items: list[Evidence]) -> list[Evidence]:
    return list({item.url: item for item in items}.values())
