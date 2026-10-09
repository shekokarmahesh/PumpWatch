import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select

from .models import Analysis, Call, HistoryPoint, PastSearch, Ticker, WatchItem


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class BudgetExceeded(ValueError):
    """A local limit rejected a request before it reached SerpApi."""


class TickerRow(SQLModel, table=True):
    __tablename__ = "tickers"
    id: str = Field(primary_key=True)
    payload: str
    on_watchlist: bool = False
    first_seen_at: str


class CallRow(SQLModel, table=True):
    __tablename__ = "calls"
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    fetched_at: str = Field(index=True)
    credits_spent: int
    status: str
    payload: str


class SignalRow(SQLModel, table=True):
    __tablename__ = "signals"
    id: str = Field(primary_key=True)
    ticker_id: str = Field(index=True)
    run_id: str = Field(index=True)
    name: str
    payload: str


class EvidenceRow(SQLModel, table=True):
    __tablename__ = "evidence"
    id: str = Field(primary_key=True)
    signal_id: str = Field(index=True)
    url: str
    payload: str


class PromoterRow(SQLModel, table=True):
    __tablename__ = "promoters"
    id: str = Field(primary_key=True)
    payload: str
    matched_at: str


class ScoreRow(SQLModel, table=True):
    __tablename__ = "scores"
    id: str = Field(primary_key=True)
    ticker_id: str = Field(index=True)
    run_at: str = Field(index=True)
    snapshot: bool
    payload: str


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 30}
        )
        SQLModel.metadata.create_all(self.engine)
        self.lock = threading.RLock()

    def save_call(self, run_id: str, call: Call):
        with self.lock, Session(self.engine) as db:
            db.merge(
                CallRow(
                    id=call.id,
                    run_id=run_id,
                    fetched_at=call.fetched_at,
                    credits_spent=call.credits_spent,
                    status=call.status,
                    payload=call.model_dump_json(),
                )
            )
            db.commit()

    def reserve(self, run_id: str, call: Call, monthly: int, hourly: int) -> bool:
        # A SQLite write transaction also serializes budget checks across CLI/server processes.
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        month_start = (
            now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        )
        hour_start = (now - timedelta(hours=1)).astimezone(timezone.utc).isoformat()
        with self.lock, Session(self.engine) as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            rows = db.exec(select(CallRow).where(CallRow.fetched_at >= month_start)).all()
            month_spend = sum(r.credits_spent for r in rows)
            hour_spend = sum(r.credits_spent for r in rows if r.fetched_at >= hour_start)
            if month_spend + call.credits_spent > monthly:
                db.rollback()
                raise BudgetExceeded(
                    f"Local monthly search budget reached ({month_spend}/{monthly} estimated requests). "
                    "Saved results are still available."
                )
            if hour_spend + call.credits_spent > hourly:
                db.rollback()
                raise BudgetExceeded(
                    f"Local hourly search limit reached ({hour_spend}/{hourly} estimated requests "
                    "in the past hour). Try again later; saved results are still available."
                )
            db.merge(
                CallRow(
                    id=call.id,
                    run_id=run_id,
                    fetched_at=call.fetched_at,
                    credits_spent=call.credits_spent,
                    status=call.status,
                    payload=call.model_dump_json(),
                )
            )
            db.commit()
            return True

    def spend(self, hours: int | None = None) -> int:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        since = (
            (now - timedelta(hours=hours)).astimezone(timezone.utc).isoformat()
            if hours
            else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc)
            .isoformat()
        )
        with Session(self.engine) as db:
            return sum(r.credits_spent for r in db.exec(select(CallRow).where(CallRow.fetched_at >= since)))

    def calls(self, run_id: str) -> list[Call]:
        with Session(self.engine) as db:
            rows = db.exec(select(CallRow).where(CallRow.run_id == run_id).order_by(CallRow.fetched_at)).all()
            return [Call.model_validate_json(r.payload) for r in rows]

    def upsert_ticker(self, ticker: Ticker, watched: bool | None = None):
        with self.lock, Session(self.engine) as db:
            row = db.get(TickerRow, ticker.key)
            if row is None:
                row = TickerRow(id=ticker.key, payload=ticker.model_dump_json(), first_seen_at=utcnow())
            row.payload = ticker.model_dump_json()
            if watched is not None:
                row.on_watchlist = watched
            db.add(row)
            db.commit()

    def save(self, result: Analysis):
        self.upsert_ticker(result.ticker)
        with self.lock, Session(self.engine) as db:
            db.add(
                ScoreRow(
                    id=result.run_id,
                    ticker_id=result.ticker.key,
                    run_at=result.run_at,
                    snapshot=result.snapshot,
                    payload=result.model_dump_json(),
                )
            )
            for signal in result.signals:
                sid = f"{result.run_id}:{signal.name}"
                db.add(
                    SignalRow(
                        id=sid,
                        ticker_id=result.ticker.key,
                        run_id=result.run_id,
                        name=signal.name,
                        payload=signal.model_dump_json(),
                    )
                )
                for i, ev in enumerate(signal.evidence):
                    db.add(
                        EvidenceRow(id=f"{sid}:{i}", signal_id=sid, url=ev.url, payload=ev.model_dump_json())
                    )
            for promoter in result.promoters:
                db.merge(
                    PromoterRow(
                        id=f"{'demo' if result.synthetic else 'live'}:{promoter.name.casefold()}",
                        payload=promoter.model_dump_json(),
                        matched_at=utcnow(),
                    )
                )
            db.commit()

    def run(self, run_id: str) -> Analysis | None:
        with Session(self.engine) as db:
            row = db.get(ScoreRow, run_id)
            return Analysis.model_validate_json(row.payload) if row else None

    def latest(self, ticker_key: str) -> Analysis | None:
        with Session(self.engine) as db:
            row = db.exec(
                select(ScoreRow)
                .where(ScoreRow.ticker_id == ticker_key)
                .order_by(ScoreRow.run_at.desc(), ScoreRow.id.desc())
                .limit(1)
            ).first()
            return Analysis.model_validate_json(row.payload) if row else None

    def ticker(self, key: str) -> Ticker | None:
        with Session(self.engine) as db:
            row = db.get(TickerRow, key)
            return Ticker.model_validate_json(row.payload) if row else None

    def watchlist(self) -> list[WatchItem]:
        with Session(self.engine) as db:
            rows = db.exec(select(TickerRow).where(TickerRow.on_watchlist)).all()
            return [
                WatchItem(ticker=Ticker.model_validate_json(r.payload), latest=self.latest(r.id))
                for r in rows
            ]

    def past_searches(self, limit: int = 50) -> list[PastSearch]:
        # Select the most recent saved run per stock, including stocks off the watchlist.
        ranked = select(
            ScoreRow.id,
            func.row_number()
            .over(
                partition_by=ScoreRow.ticker_id,
                order_by=(ScoreRow.run_at.desc(), ScoreRow.id.desc()),
            )
            .label("rank"),
            func.count().over(partition_by=ScoreRow.ticker_id).label("run_count"),
        ).subquery()
        statement = (
            select(ScoreRow, ranked.c.run_count)
            .join(ranked, ScoreRow.id == ranked.c.id)
            .where(ranked.c.rank == 1)
            .order_by(ScoreRow.run_at.desc(), ScoreRow.id.desc())
            .limit(limit)
        )
        with Session(self.engine) as db:
            return [
                PastSearch(**Analysis.model_validate_json(row.payload).model_dump(), run_count=count)
                for row, count in db.exec(statement).all()
            ]

    def today_snapshot(self, key: str, mode: str) -> Analysis | None:
        day = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        for result in reversed(self.results(key)):
            date = (
                datetime.fromisoformat(result.run_at).astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
            )
            if result.snapshot and date == day and result.mode == mode:
                return result
        return None

    def results(self, key: str) -> list[Analysis]:
        with Session(self.engine) as db:
            return [
                Analysis.model_validate_json(r.payload)
                for r in db.exec(
                    select(ScoreRow).where(ScoreRow.ticker_id == key).order_by(ScoreRow.run_at)
                ).all()
            ]

    def history(self, key: str, days: int) -> list[HistoryPoint]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        seen_promoters, seen_ads, daily = set(), set(), {}
        for result in self.results(key):
            names = {p.name.casefold() for p in result.promoters}
            ads = {e.url for s in result.signals if s.name == "paid_promotion" for e in s.evidence}
            has_prior = bool(daily)
            date = (
                datetime.fromisoformat(result.run_at).astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
            )
            previous = daily.get(date)
            daily[date] = HistoryPoint(
                run_id=result.run_id,
                date=date,
                hype_score=result.hype_score,
                support_score=result.support_score,
                verdict=result.verdict,
                new_promoter=(has_prior and bool(names - seen_promoters))
                or bool(previous and previous.new_promoter),
                new_ad=(has_prior and bool(ads - seen_ads)) or bool(previous and previous.new_ad),
                snapshot=result.snapshot,
                carried=any(s.carried for s in result.signals),
                synthetic=result.synthetic,
            )
            seen_promoters |= names
            seen_ads |= ads
        return [point for date, point in daily.items() if date >= cutoff[:10]]
