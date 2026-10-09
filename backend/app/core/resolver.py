import csv
import re
import time
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

from .cache import Cache
from .models import Ticker
from .normalize import company_query

SYMBOL = r"[A-Za-z0-9&._-]{1,30}"
LEGAL_WORDS = {"limited", "ltd", "inc", "plc", "ord", "shs", "share", "shares", "price", "stock"}


def name_words(value: str) -> list[str]:
    return [word for word in re.findall(r"\w+", value.casefold()) if word not in LEGAL_WORDS]


def matches_company(query: str, ticker: Ticker) -> bool:
    words = name_words(query)
    company = name_words(ticker.company_name)
    return bool(words) and (
        "".join(words) == ticker.symbol.casefold()
        or all(any(word.startswith(part) for word in company) for part in words)
    )


def quote_identity(link: str) -> tuple[str, str] | None:
    """Only take listing identifiers from Google Finance or official exchange URLs."""
    url = urlparse(link)
    if url.scheme not in {"https", "http"}:
        return None
    path = unquote(url.path)
    if url.hostname in {"google.com", "www.google.com"}:
        match = re.fullmatch(rf"/finance/quote/({SYMBOL}):(NSE|BOM|BSE)/?", path, re.I)
        if match:
            return match[1].upper(), "BOM" if match[2].upper() == "BSE" else match[2].upper()
    if url.hostname in {"nseindia.com", "www.nseindia.com"} and path in {
        "/get-quotes/equity",
        "/market-data/issue-information",
    }:
        symbol = parse_qs(url.query).get("symbol", [""])[0]
        if re.fullmatch(SYMBOL, symbol):
            return symbol.upper(), "NSE"
    if url.hostname in {"bseindia.com", "www.bseindia.com"}:
        match = re.match(r"^/stock-share-price/[^/]+/[^/]+/(\d{6})(?:/|$)", path, re.I)
        if match:
            return match[1], "BOM"
    return None


def listing_title(title: str) -> str:
    return re.split(
        r"\s+(?:shareholding\b|share/?stock price\b|share price\b|stock price\b)|\s+[|–—]\s+",
        title,
        maxsplit=1,
        flags=re.I,
    )[0].strip()


class Resolver:
    def __init__(self, cache: Cache):
        self.cache = cache
        self.examples = [Ticker.model_validate(t) for t in cache.manifest["tickers"]]
        self.sme = {}
        for path in (cache.settings.data_dir / "exchanges").glob("*.csv"):
            for row in csv.DictReader(path.read_text().splitlines()):
                self.sme[f"{row['symbol']}:{row['exchange']}"] = row

    def decorate(self, ticker: Ticker) -> Ticker:
        if not ticker.synthetic:
            ticker.company_name = company_query(ticker.company_name)
        if not ticker.synthetic and ticker.key in self.sme:
            ticker.is_sme, ticker.listing_verified = True, True
        return ticker

    async def resolve(self, query: str) -> list[Ticker]:
        query = " ".join(query.split())
        if not query:
            raise ValueError("Enter a ticker or company name")
        if self.cache.settings.mode == "replay":
            candidates = [
                t
                for t in self.examples
                if query.casefold() in t.key.casefold() or query.casefold() in t.company_name.casefold()
            ]
            if not candidates:
                raise ValueError("Replay supports the five bundled fictional examples. Select one below.")
            return candidates[:5]
        run_id, deadline = f"resolve-{uuid4().hex}", time.monotonic() + 30
        explicit = re.fullmatch(rf"({SYMBOL})\s*:\s*(NSE|BOM|BSE)", query, re.I)
        if explicit:
            exchange = explicit[2].upper()
            key = f"{explicit[1].upper()}:{'BOM' if exchange == 'BSE' else exchange}"
            existing = self.cache.store.ticker(key)
            if existing and not existing.synthetic:
                return [self.decorate(existing)]
            candidates = await self._finance(key, run_id, deadline)
        elif ":" in query:
            raise ValueError("Search by company name, or use an Indian symbol such as RELIANCE:NSE.")
        else:
            # Try bare symbols directly, then discover the listing when the input is a name.
            if re.fullmatch(SYMBOL, query):
                key = f"{query.upper()}:{'BOM' if query.isdigit() else 'NSE'}"
                candidates = await self._finance(key, run_id, deadline)
                exact = next((t for t in candidates if t.key == key), None)
                if exact:
                    return [exact]
            raw, call = await self.cache.fetch(
                {"engine": "google", "q": f"{query.casefold()} share price", "gl": "in", "hl": "en"},
                run_id,
                deadline,
                request_timeout=20,
            )
            if call.status == "error":
                if "timed out" in (call.error or ""):
                    raise ValueError("Company search took too long. Please try again.")
                raise ValueError(call.error or "Company search is unavailable. Please try again.")
            candidates = self._name_candidates(raw, query)
            if candidates:
                # Verify the leading search match and replace search-page titles with the canonical name.
                top = candidates[0]
                verified = await self._finance(top.key, run_id, deadline)
                confirmed = next(
                    (t for t in verified if t.key == top.key and matches_company(query, t)), None
                )
                if confirmed:
                    candidates[0] = confirmed
                    self.cache.store.upsert_ticker(confirmed)
                else:
                    candidates = candidates[1:]
        if not candidates:
            raise ValueError(
                "No matching Indian listing found. Try a fuller company name; very new listings may not be indexed yet."
            )
        return candidates[:5]

    def _tickers(self, rows: list[dict]) -> list[Ticker]:
        candidates = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            stock = str(row.get("stock") or row.get("symbol") or "")
            exchange = str(row.get("exchange", "")).upper()
            if ":" in stock:
                stock, exchange = stock.split(":", 1)
            exchange = exchange.upper()
            if exchange == "BSE":
                exchange = "BOM"
            title = row.get("title") or row.get("name")
            if exchange in {"NSE", "BOM"} and re.fullmatch(SYMBOL, stock) and title:
                candidates.append(
                    self.decorate(Ticker(symbol=stock.upper(), exchange=exchange, company_name=title))
                )
        unique = {}
        for ticker in candidates:
            unique.setdefault(ticker.key, ticker)
        return list(unique.values())

    async def _finance(self, key: str, run_id: str, deadline: float) -> list[Ticker]:
        raw, call = await self.cache.fetch(
            {"engine": "google_finance", "q": key, "window": "1M", "hl": "en"}, run_id, deadline
        )
        if call.status == "error":
            raise ValueError(call.error or "Listing lookup is unavailable. Please try again.")
        return self._tickers([raw.get("summary", {})] + raw.get("suggestions", []))

    def _name_candidates(self, raw: dict, query: str) -> list[Ticker]:
        answer = raw.get("answer_box", {})
        rows = [answer] if isinstance(answer, dict) and answer.get("type") == "finance_results" else []
        knowledge = raw.get("knowledge_graph", {})
        if isinstance(knowledge, dict) and knowledge.get("entity_type") == "finance":
            match = re.fullmatch(rf"(NSE|BSE|BOM):\s*({SYMBOL})", knowledge.get("type", ""), re.I)
            if match:
                rows.append({"exchange": match[1], "stock": match[2], "title": knowledge.get("title")})
        for result in raw.get("organic_results", []):
            identity = quote_identity(result.get("link", ""))
            if identity and result.get("title"):
                rows.append(
                    {"stock": identity[0], "exchange": identity[1], "title": listing_title(result["title"])}
                )
        # Filter before deduplicating: a finance answer titled "News" must not
        # hide the same listing's company name in the knowledge graph or links.
        candidates = {}
        for row in rows:
            for ticker in self._tickers([row]):
                if matches_company(query, ticker):
                    candidates.setdefault(ticker.key, ticker)
        return sorted(
            candidates.values(),
            key=lambda t: (name_words(query) != name_words(t.company_name), t.exchange != "NSE"),
        )

    async def get(self, symbol: str, exchange: str) -> Ticker:
        key = f"{symbol.upper()}:{exchange}"
        if self.cache.settings.mode == "replay":
            return next((t for t in self.examples if t.key == key), None) or self._missing()
        existing = self.cache.store.ticker(key)
        if existing and not existing.synthetic:
            return self.decorate(existing)
        candidates = await self.resolve(key)
        return next((t for t in candidates if t.key == key), None) or self._missing()

    @staticmethod
    def _missing():
        raise ValueError("No matching Indian stock was resolved. Confirm the symbol and exchange.")
