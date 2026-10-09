import asyncio
import json
import time

import pytest

from app.core.cache import Cache, params_hash
from app.core.config import Settings
from app.core.store import Store


async def test_concurrent_identical_calls_are_coalesced_and_raw_persisted(tmp_path, monkeypatch):
    settings = Settings(mode="cache-first", api_key="test-key", state_dir=tmp_path)
    store = Store(tmp_path / "state.sqlite")
    cache = Cache(settings, store)
    invoked = []

    async def fake(params, deadline, **kwargs):
        invoked.append(params)
        await asyncio.sleep(0.01)
        return {
            "summary": {"title": "Real response"},
            "search_parameters": {"api_key": "test-key"},
            "next": "https://serpapi.com/search?api_key=test-key",
        }

    monkeypatch.setattr(cache, "_request", fake)
    params = {"engine": "google_finance", "q": "TEST:NSE"}
    results = await asyncio.gather(*(cache.fetch(params, str(i), time.monotonic() + 10) for i in range(4)))
    assert len(invoked) == 1
    assert sum(c.credits_spent for _, c in results) == 1
    raw = json.loads((tmp_path / "cache" / f"{params_hash(params)}.json").read_text())
    assert "api_key" not in raw["search_parameters"]
    assert "test-key" not in json.dumps(raw)
    assert sum(c.cache_hit for _, c in results) == 3


async def test_credit_reservations_cap_concurrent_requests(tmp_path, monkeypatch):
    settings = Settings(mode="live", api_key="test-key", state_dir=tmp_path, monthly_budget=1)
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))

    async def fake(params, deadline, **kwargs):
        await asyncio.sleep(0.01)
        return {"result": "ok"}

    monkeypatch.setattr(cache, "_request", fake)
    results = await asyncio.gather(
        *(cache.fetch({"engine": "google", "q": str(i)}, "run", time.monotonic() + 10) for i in range(3))
    )
    assert sum(c.status == "success" for _, c in results) == 1
    assert cache.store.spend() == 1


async def test_default_hourly_budget_allows_more_than_fifty_requests(tmp_path, monkeypatch):
    monkeypatch.delenv("PUMPWATCH_HOURLY_BUDGET", raising=False)
    settings = Settings(mode="live", api_key="test-key", state_dir=tmp_path)
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))

    async def fake(params, deadline, **kwargs):
        return {"result": "ok"}

    monkeypatch.setattr(cache, "_request", fake)
    results = await asyncio.gather(
        *(cache.fetch({"engine": "google", "q": str(i)}, "run", time.monotonic() + 10) for i in range(51))
    )
    assert all(call.status == "success" for _, call in results)
    assert cache.store.spend(hours=1) == 51


@pytest.mark.parametrize("window", ["hourly", "monthly"])
async def test_budget_error_names_the_limit_without_charging_blocked_or_cached_requests(
    tmp_path, monkeypatch, window
):
    settings = Settings(
        mode="live",
        api_key="test-key",
        state_dir=tmp_path,
        hourly_budget=1 if window == "hourly" else 250,
        monthly_budget=1 if window == "monthly" else 250,
    )
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))
    invoked = []

    async def fake(params, deadline, **kwargs):
        invoked.append(params)
        return {"result": "ok"}

    monkeypatch.setattr(cache, "_request", fake)
    params = {"engine": "google", "q": "first"}
    await cache.fetch(params, "run", time.monotonic() + 10)
    raw, blocked = await cache.fetch({"engine": "google", "q": "second"}, "run", time.monotonic() + 10)
    assert raw == {} and blocked.status == "error"
    assert f"Local {window}" in blocked.error
    assert "1/1" in blocked.error
    assert blocked.credits_spent == 0
    assert cache.store.spend() == 1
    raw, cached = await cache.fetch(params, "run", time.monotonic() + 10)
    assert raw["result"] == "ok" and cached.cache_hit and cached.credits_spent == 0
    assert len(invoked) == 1


async def test_replay_refuses_unknown_parameters(settings, monkeypatch):
    cache = Cache(settings, Store(settings.state_dir / "state.sqlite"))

    async def forbidden(*args):
        raise AssertionError("Network attempted")

    monkeypatch.setattr(cache, "_request", forbidden)
    raw, call = await cache.fetch({"engine": "google", "q": "unknown"}, "test", time.monotonic() + 1)
    assert raw == {} and call.status == "error" and call.credits_spent == 0


async def test_request_timeout_allows_slow_searches_but_respects_deadline(tmp_path, monkeypatch):
    import serpapi

    timeouts = []

    class Client:
        def __init__(self, api_key, timeout):
            timeouts.append(timeout)

        def search(self, params):
            return {"organic_results": []}

    monkeypatch.setattr(serpapi, "Client", Client)
    settings = Settings(mode="live", api_key="test-key", state_dir=tmp_path)
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))
    await cache._request({"engine": "google"}, time.monotonic() + 25)
    await cache._request({"engine": "google"}, time.monotonic() + 2)
    await cache._request({"engine": "google"}, time.monotonic() + 30, request_timeout=20)
    await cache._request({"engine": "google"}, time.monotonic() + 3, request_timeout=20)
    assert timeouts[0] == 12
    assert 0 < timeouts[1] <= 2
    assert timeouts[2] == 20
    assert 0 < timeouts[3] <= 3


async def test_no_results_response_has_a_specific_reason(tmp_path, monkeypatch):
    settings = Settings(mode="live", api_key="test-key", state_dir=tmp_path)
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))

    async def fake(params, deadline, **kwargs):
        return {
            "search_metadata": {"status": "Success"},
            "error": "Google hasn't returned any results for this query.",
        }

    monkeypatch.setattr(cache, "_request", fake)
    raw, call = await cache.fetch({"engine": "google", "q": "empty"}, "run", time.monotonic() + 20)
    assert raw == {}
    assert call.status == "empty"
    assert call.error == "The provider returned no results for this query."


async def test_failed_provider_response_does_not_poison_the_cache(tmp_path, monkeypatch):
    settings = Settings(mode="live", api_key="test-key", state_dir=tmp_path)
    cache = Cache(settings, Store(tmp_path / "state.sqlite"))
    params = {"engine": "google", "q": "recoverable"}
    path = tmp_path / "cache" / f"{params_hash(params)}.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"error": "Transient provider error"}))

    async def fake(params, deadline, **kwargs):
        return {"organic_results": [{"title": "Recovered", "link": "https://example.com"}]}

    monkeypatch.setattr(cache, "_request", fake)
    raw, call = await cache.fetch(params, "run", time.monotonic() + 20)
    assert raw["organic_results"][0]["title"] == "Recovered"
    assert call.status == "success" and not call.cache_hit
