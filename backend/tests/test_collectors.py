import json
import shutil
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core.collectors.finance import daily_graph
from app.core.models import Ticker
from app.core.normalize import has_keyword, names_stock, parsed_date
from app.core.registry import Registry


async def test_captured_youtube_compact_dates_produce_an_available_signal():
    from pathlib import Path

    from app.core.collectors import youtube
    from app.core.collectors.base import Context
    from app.core.models import Call

    raw = json.loads((Path(__file__).parent / "fixtures/compact_youtube.json").read_text())

    class CapturedCache:
        async def fetch(self, params, run_id, deadline):
            return raw, Call(
                id=params["sp"],
                engine="youtube",
                params=params,
                params_hash="captured",
                mode="cache",
                cache_hit=True,
                credits_spent=0,
                raw_path=None,
                fetched_at=raw["_pumpwatch_fetched_at"],
                status="success",
            )

    ctx = Context(
        Ticker(symbol="ORIENTCABL", exchange="NSE", company_name="Orient Cables (India) Ltd"),
        CapturedCache(),
        "captured-run",
        datetime(2026, 10, 8, 11, tzinfo=timezone.utc),
        0,
    )
    result = (await youtube.collect(ctx))[0]
    assert result.has_data, "A successful, dated YouTube sample was incorrectly displayed as No data"
    assert result.evidence[0].published_at is not None


@pytest.mark.parametrize(
    "value,days", [("6d ago", 6), ("Streamed 2w ago", 14), ("3mo ago", 90), ("1y ago", 365)]
)
def test_compact_dates(value, days):
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    assert (now - parsed_date(value, now)).days == days


def test_provider_display_suffixes_do_not_break_stock_attribution():
    assert names_stock(
        "Orient Cables share target",
        Ticker(symbol="ORIENTCABL", exchange="NSE", company_name="Orient Cables (India) Ltd"),
    )
    assert names_stock(
        "Moneyview share target", Ticker(symbol="MONEYVIEW", exchange="NSE", company_name="Moneyview Ord Shs")
    )
    assert not names_stock(
        "Orient Electric target",
        Ticker(symbol="ORIENTCABL", exchange="NSE", company_name="Orient Cables (India) Ltd"),
    )


async def test_new_listing_needs_volume_history_older_than_current_month():
    from app.core.collectors import finance
    from app.core.collectors.base import Context
    from app.core.models import Call

    raw = {"graph": [{"date": f"2026-10-0{day}", "price": 100 + day, "volume": 1000} for day in [5, 6, 7]]}

    class CapturedCache:
        async def fetch(self, params, run_id, deadline):
            return raw, Call(
                id=params["window"],
                engine="google_finance",
                params=params,
                params_hash="captured",
                mode="cache",
                cache_hit=True,
                credits_spent=0,
                raw_path=None,
                fetched_at="2026-10-08T00:00:00+00:00",
                status="success",
            )

    ctx = Context(
        Ticker(symbol="ORIENTCABL", exchange="NSE", company_name="Orient Cables (India) Ltd"),
        CapturedCache(),
        "captured-run",
        datetime(2026, 10, 8, tzinfo=timezone.utc),
        0,
    )
    result = (await finance.collect(ctx))[0]
    assert not result.has_data, "The same three listing days cannot establish a historical volume baseline"
    assert result.score is None


def test_daily_volume_aggregates_intraday_points():
    as_of = datetime(2026, 10, 8, tzinfo=timezone.utc)
    raw = {
        "graph": [
            {"date": "2026-10-07T10:00:00+00:00", "price": 100, "volume": 2},
            {"date": "2026-10-07T11:00:00+00:00", "price": 110, "volume": 3},
            {"date": "2026-10-08T10:00:00+00:00", "price": 120, "volume": 5},
        ]
    }
    prices, volumes = daily_graph(raw, as_of)
    assert prices == [100, 110, 120]
    assert volumes == [5, 5]


def test_keyword_boundaries_and_company_attribution():
    assert has_keyword("टारगेट kharido breakout")
    assert not has_keyword("buyers at a supermarket")
    assert names_stock(
        "Pulse Components target", Ticker(symbol="PULSE", exchange="NSE", company_name="Pulse Components")
    )
    assert not names_stock(
        "Unrelated stock target", Ticker(symbol="PULSE", exchange="NSE", company_name="Pulse Components")
    )


def test_dates_and_registry_unknown(settings):
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    assert (now - parsed_date("2 weeks ago", now)).days == 14
    assert now - parsed_date("2h ago", now) == timedelta(hours=2)
    assert now - parsed_date("15m ago", now) == timedelta(minutes=15)
    assert parsed_date("unknown", now) is None
    assert parsed_date("May 22 2026, 09:30 AM UTC-04:00", now).utcoffset().total_seconds() == -14400
    assert Registry(settings.data_dir).match("Real Person").status == "not_checked"
    demo = Registry(settings.data_dir, synthetic=True)
    assert demo.match("measured markets!").status == "registered"
    assert demo.match("Measured Market").status == "possible"
    assert demo.match("Rocket Tips").status == "not_found"


@pytest.mark.parametrize("issue", ["empty", "stale", "future"])
def test_incomplete_or_invalid_date_registry_is_not_authoritative(settings, tmp_path, issue):
    data_dir = tmp_path / "data"
    shutil.copytree(settings.data_dir / "registry", data_dir / "registry")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    captured = today + timedelta(days=1 if issue == "future" else -31 if issue == "stale" else 0)
    folder = data_dir / "registry"
    (folder / "metadata.json").write_text(
        json.dumps(
            {
                "verified_complete": True,
                "captured_at": captured.isoformat(),
                "source_url": "https://www.sebi.gov.in/registry",
            }
        )
    )
    if issue != "empty":
        for name in ["research_analysts.csv", "investment_advisers.csv"]:
            (folder / name).write_text(
                "name,registration_number,registry_type,valid_until\nKnown Name,TEST001,RA,2099-12-31\n"
            )
    assert Registry(data_dir).match("Real Person").status == "not_checked"
