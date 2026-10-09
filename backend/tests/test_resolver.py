import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.models import Ticker
from app.core.resolver import matches_company, quote_identity
from app.main import create_app


@pytest.mark.parametrize(
    "query,search,key,company",
    [
        (
            "  Jindal   Supreme  ",
            {
                "answer_box": {
                    "type": "finance_results",
                    "stock": "JSIPL",
                    "exchange": "NSE",
                    "title": "Jindal Supreme India Ord Shs",
                },
                "organic_results": [
                    {
                        "title": "Jindal Steel share price",
                        "link": "https://www.google.com/finance/quote/JINDALSTEL:NSE",
                    }
                ],
            },
            "JSIPL:NSE",
            "Jindal Supreme India",
        ),
        (
            "Adroit Industries",
            {
                "organic_results": [
                    {
                        "title": "Adroit Industries India Ltd Shareholding Pattern, Adroitind",
                        "link": "https://www.bseindia.com/stock-share-price/adroit-industries-india-ltd/adroitind/544950/shp",
                    }
                ]
            },
            "544950:BOM",
            "Adroit Industries (India) Limited",
        ),
        *[
            (
                query,
                {
                    "answer_box": {
                        "type": "finance_results",
                        "stock": symbol,
                        "exchange": "NSE",
                        "title": "News",
                    },
                    "knowledge_graph": {
                        "entity_type": "finance",
                        "type": f"NSE: {symbol}",
                        "title": company,
                    },
                },
                f"{symbol}:NSE",
                company,
            )
            for query, symbol, company in [
                ("Reliance Industries", "RELIANCE", "Reliance Industries Ltd"),
                ("ESDS Software", "ESDS", "ESDS Software Solution Ltd"),
            ]
        ],
    ],
)
def test_company_names_resolve_and_confirm_without_repeating_discovery(
    tmp_path, monkeypatch, query, search, key, company
):
    app = create_app(Settings(mode="live", api_key="test-key", state_dir=tmp_path))
    service, requests = app.state.service, []

    async def provider(params, deadline, request_timeout):
        requests.append(params)
        if params["engine"] == "google":
            assert request_timeout == 20
            assert params["q"] == " ".join(query.casefold().split()) + " share price"
            return search
        assert params["q"] == key
        return {"summary": {"stock": key, "title": company + " Ord Shs"}}

    monkeypatch.setattr(service.cache, "_request", provider)
    with TestClient(app) as client:
        response = client.post("/api/resolve", json={"query": query})
        assert response.status_code == 200, response.text
        assert [f"{t['symbol']}:{t['exchange']}" for t in response.json()] == [key]
        assert response.json()[0]["company_name"] == company
        assert client.post("/api/resolve", json={"query": query.upper()}).json() == response.json()
    assert len(requests) == 2
    assert service.store.ticker(key).company_name == company
    assert service.store.spend() == 2


async def test_confirmation_uses_persisted_listing(tmp_path, monkeypatch):
    app = create_app(Settings(mode="live", api_key="test-key", state_dir=tmp_path))
    resolver = app.state.service.resolver
    ticker = Ticker(symbol="JSIPL", exchange="NSE", company_name="Jindal Supreme India")
    resolver.cache.store.upsert_ticker(ticker)

    async def forbidden(*args):
        raise AssertionError("Confirmed listing should not trigger a lookup")

    monkeypatch.setattr(resolver.cache, "fetch", forbidden)
    assert await resolver.get("JSIPL", "NSE") == ticker


def test_partial_names_offer_multiple_indian_matches_and_ignore_foreign_results(tmp_path, monkeypatch):
    app = create_app(Settings(mode="live", api_key="test-key", state_dir=tmp_path))

    async def provider(params, deadline, **kwargs):
        if params["engine"] == "google_finance":
            return {"summary": {"stock": "JSIPL:NSE", "title": "Jindal Supreme India"}}
        return {
            "organic_results": [
                {
                    "title": "Jindal Supreme India Stock Price & News",
                    "link": "https://www.google.com/finance/quote/JSIPL:NSE",
                },
                {
                    "title": "Jindal Steel Ltd Share Price",
                    "link": "https://www.nseindia.com/get-quotes/equity?symbol=JINDALSTEL",
                },
                {"title": "Jindal abroad", "link": "https://www.google.com/finance/quote/JINDAL:NASDAQ"},
                {"title": "Jindal made up", "link": "https://example.com/finance/quote/FAKE:NSE"},
            ]
        }

    monkeypatch.setattr(app.state.service.cache, "_request", provider)
    with TestClient(app) as client:
        rows = client.post("/api/resolve", json={"query": "jindal"}).json()
    assert [row["symbol"] for row in rows] == ["JSIPL", "JINDALSTEL"]


@pytest.mark.parametrize(
    "query,key",
    [
        ("jsipl : nse", "JSIPL:NSE"),
        ("544950:bse", "544950:BOM"),
        ("JSIPL", "JSIPL:NSE"),
        ("jsipl", "JSIPL:NSE"),
        ("544950", "544950:BOM"),
    ],
)
def test_explicit_symbols_still_work_and_accept_exchange_aliases(tmp_path, monkeypatch, query, key):
    app = create_app(Settings(mode="live", api_key="test-key", state_dir=tmp_path))

    async def provider(params, deadline, **kwargs):
        assert params["engine"] == "google_finance" and params["q"] == key
        return {"summary": {"stock": key, "title": "Test company"}}

    monkeypatch.setattr(app.state.service.cache, "_request", provider)
    with TestClient(app) as client:
        response = client.post("/api/resolve", json={"query": query})
    assert response.status_code == 200


def test_unknown_name_gets_helpful_message_without_accepting_unrelated_stock(tmp_path, monkeypatch):
    app = create_app(Settings(mode="live", api_key="test-key", state_dir=tmp_path))

    async def provider(params, deadline, **kwargs):
        return {
            "answer_box": {
                "type": "finance_results",
                "stock": "JINDALSTEL",
                "exchange": "NSE",
                "title": "Jindal Steel",
            }
        }

    monkeypatch.setattr(app.state.service.cache, "_request", provider)
    with TestClient(app) as client:
        response = client.post("/api/resolve", json={"query": "jindal supreme"})
    assert response.status_code == 400
    assert "Try a fuller company name" in response.json()["detail"]
    assert app.state.service.store.spend() == 1


def test_partial_words_and_symbols_match_without_conflating_different_companies():
    ticker = Ticker(symbol="ORIENTCABL", exchange="NSE", company_name="Orient Cables (India) Ltd")
    assert matches_company("orient cable", ticker)
    assert matches_company("ORIENTCABL", ticker)
    assert not matches_company("orient electric", ticker)
    assert not matches_company("Limited", ticker)
    assert not matches_company(
        "Bank of India", Ticker(symbol="MAHABANK", exchange="NSE", company_name="Bank of Maharashtra")
    )


@pytest.mark.parametrize(
    "link,expected",
    [
        ("https://www.google.com/finance/quote/JSIPL%3ANSE?hl=en", ("JSIPL", "NSE")),
        (
            "https://www.nseindia.com/market-data/issue-information?symbol=ADROITIND&series=EQ",
            ("ADROITIND", "NSE"),
        ),
        ("https://www.google.com/finance/quote/MSFT:NASDAQ", None),
        ("https://www.google.com.example.com/finance/quote/FAKE:NSE", None),
    ],
)
def test_listing_identity_comes_from_supported_exchange_urls(link, expected):
    assert quote_identity(link) == expected
