from typing import Any, Literal

from pydantic import BaseModel, Field


class Ticker(BaseModel):
    symbol: str
    exchange: Literal["NSE", "BOM"]
    company_name: str
    is_sme: bool = False
    listing_verified: bool = False
    synthetic: bool = False

    @property
    def key(self) -> str:
        return f"{self.symbol}:{self.exchange}"


class RegistryMatch(BaseModel):
    name: str
    status: Literal["registered", "possible", "not_found", "not_checked"]
    similarity: float | None = None
    registry_row: dict[str, str] | None = None
    note: str = ""


class Evidence(BaseModel):
    url: str
    title: str
    source: str
    published_at: str | None = None
    promoter_name: str | None = None
    promoter: RegistryMatch | None = None
    synthetic: bool = False


class Signal(BaseModel):
    name: str
    label: str
    side: Literal["hype", "support"]
    value: float | None = None
    unit: str = ""
    window: str
    has_data: bool = False
    score: float | None = None
    weight: float
    rule: str
    explanation: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    call_ids: list[str] = Field(default_factory=list)
    carried: bool = False


class Call(BaseModel):
    id: str
    engine: str
    params: dict[str, Any]
    params_hash: str
    mode: Literal["live", "cache", "replay"]
    cache_hit: bool
    credits_spent: int
    raw_path: str | None
    fetched_at: str
    status: str
    error: str | None = None
    synthetic: bool = False


class Reason(BaseModel):
    signal_name: str
    title: str
    explanation: str
    score: float
    evidence: list[Evidence]


class Analysis(BaseModel):
    run_id: str
    ticker: Ticker
    run_at: str
    data_as_of: str
    mode: Literal["live", "cache-first", "replay"]
    synthetic: bool
    hype_score: float | None
    support_score: float | None
    verdict: Literal["Low", "Elevated", "High", "Insufficient data"]
    signals_available: int
    support_available: int
    reasons: list[Reason]
    signals: list[Signal]
    promoters: list[RegistryMatch]
    warnings: list[str]
    disclaimer: str
    snapshot: bool = False


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)


class TickerRequest(BaseModel):
    symbol: str = Field(pattern=r"^[A-Za-z0-9&._-]{1,30}$")
    exchange: Literal["NSE", "BOM"] = "NSE"


class WatchItem(BaseModel):
    ticker: Ticker
    latest: Analysis | None


class PastSearch(BaseModel):
    ticker: Ticker
    run_id: str
    run_at: str
    hype_score: float | None
    support_score: float | None
    verdict: str
    signals_available: int
    support_available: int
    mode: str
    synthetic: bool
    run_count: int


class HistoryPoint(BaseModel):
    run_id: str
    date: str
    hype_score: float | None
    support_score: float | None
    verdict: str
    new_promoter: bool
    new_ad: bool
    snapshot: bool
    carried: bool
    synthetic: bool


class SnapshotRequest(BaseModel):
    symbol: str | None = Field(default=None, pattern=r"^[A-Za-z0-9&._-]{1,30}$")
    exchange: Literal["NSE", "BOM"] = "NSE"


class SnapshotResponse(BaseModel):
    rows_written: int
    run_ids: list[str]
    skipped: int


class Health(BaseModel):
    status: str
    mode: str
    credits_spent_this_month: int
    credit_budget: int
    credits_spent_this_hour: int
    hourly_credit_budget: int
    credit_accounting: str
    fixture_tickers: list[Ticker]
    fixture_provenance: str
    registry_ready: bool
    disclaimer: str
