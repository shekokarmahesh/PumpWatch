import time

import pytest


@pytest.mark.parametrize(
    "symbol,exchange,verdict,hype,support",
    [
        ("PULSE", "NSE", "High", 100, 0),
        ("ASTER", "NSE", "Elevated", 43.12, 22.5),
        ("NORTHSTAR", "NSE", "Low", 0.74, 100),
        ("ORBIT", "BOM", "Low", 0, 90),
        ("SPARROW", "BOM", "Insufficient data", 13.33, None),
    ],
)
def test_five_replay_scenarios(client, symbol, exchange, verdict, hype, support):
    start = time.monotonic()
    response = client.post("/api/analyse", json={"symbol": symbol, "exchange": exchange})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["verdict"] == verdict
    assert result["hype_score"] == pytest.approx(hype, abs=0.02)
    assert result["support_score"] == support
    assert result["synthetic"] is True
    assert len(result["signals"]) == 8
    assert time.monotonic() - start < 2
    for s in result["signals"]:
        if s["has_data"]:
            assert s["evidence"]
    calls = client.get(f"/api/runs/{result['run_id']}/calls").json()
    assert len(calls) == 8
    assert all(c["credits_spent"] == 0 and c["mode"] == "replay" for c in calls)
    assert client.get("/api/health").json()["credits_spent_this_month"] == 0
    assert client.get(f"/api/runs/{result['run_id']}").json() == result


def test_resolution_export_watchlist_and_snapshot(client):
    assert client.post("/api/resolve", json={"query": "pulse"}).json()[0]["symbol"] == "PULSE"
    assert client.post("/api/resolve", json={"query": "RELIANCE:NSE"}).status_code == 400
    ticker = {"symbol": "PULSE", "exchange": "NSE"}
    result = client.post("/api/analyse", json=ticker).json()
    assert len(client.post("/api/watchlist", json=ticker).json()) == 1
    assert len(client.post("/api/watchlist", json=ticker).json()) == 1
    run = result["run_id"]
    md = client.get(f"/api/runs/{run}/export?format=md")
    assert "FICTIONAL DEMO" in md.text and result["disclaimer"] in md.text
    assert "attachment" in md.headers["content-disposition"]
    assert "calls" in client.get(f"/api/runs/{run}/export?format=json").json()
    first = client.post("/api/snapshot", json={}).json()
    assert first["rows_written"] == 1
    snapshot_run = first["run_ids"][0]
    assert len(client.get(f"/api/runs/{snapshot_run}/calls").json()) == 3
    snapshot = client.get(f"/api/runs/{snapshot_run}").json()
    assert snapshot["hype_score"] == 100
    assert any(s["carried"] for s in snapshot["signals"])
    assert client.post("/api/snapshot", json={}).json()["skipped"] == 1
    history = client.get("/api/tickers/PULSE/history").json()
    assert len(history) == 1 and history[0]["carried"]
    assert client.request("DELETE", "/api/watchlist", json=ticker).json() == []


def test_api_validation_and_missing_runs(client):
    assert client.post("/api/analyse", json={"symbol": "../secret"}).status_code == 422
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/tickers/PULSE/history?days=0").status_code == 422
    assert client.get("/api/unknown").status_code == 404


def test_health_exposes_both_local_budget_windows(client, settings):
    health = client.get("/api/health").json()
    assert health["credits_spent_this_hour"] == 0
    assert health["hourly_credit_budget"] == settings.hourly_budget
    assert health["credit_budget"] == settings.monthly_budget


def test_past_searches_persist_across_restart_and_open_without_collection(client, settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    assert client.get("/api/searches").json() == []
    client.post("/api/analyse", json={"symbol": "PULSE"})
    client.post("/api/analyse", json={"symbol": "ASTER"})
    last = client.post("/api/analyse", json={"symbol": "PULSE"}).json()
    searches = client.get("/api/searches").json()
    assert [s["ticker"]["symbol"] for s in searches] == ["PULSE", "ASTER"]
    assert searches[0]["run_id"] == last["run_id"]
    assert searches[0]["run_count"] == 2
    assert len(client.get("/api/searches?limit=1").json()) == 1
    assert client.get("/api/searches?limit=0").status_code == 422
    restarted_app = create_app(settings)
    with TestClient(restarted_app) as restarted:
        assert restarted.get("/api/searches").json() == searches
        before = len(restarted_app.state.service.store.calls(last["run_id"]))
        assert restarted.get("/api/tickers/PULSE/latest").json() == last
        assert len(restarted_app.state.service.store.calls(last["run_id"])) == before
        assert restarted.get("/api/health").json()["credits_spent_this_month"] == 0
