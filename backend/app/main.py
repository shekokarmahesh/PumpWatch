import json
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .core.config import DISCLAIMER, ROOT, Settings
from .core.models import (
    Analysis,
    Call,
    Health,
    HistoryPoint,
    PastSearch,
    QueryRequest,
    SnapshotRequest,
    SnapshotResponse,
    Ticker,
    TickerRequest,
    WatchItem,
)
from .core.registry import Registry
from .core.service import Service


def markdown_report(result: Analysis) -> str:
    lines = [
        f"# PumpWatch · {result.ticker.company_name}",
        "",
        DISCLAIMER,
        "",
        f"Ticker: {result.ticker.key} · Mode: {result.mode} · Run: {result.run_at}",
        f"Data as of: {result.data_as_of}",
        "",
        f"Verdict: {result.verdict} attention risk · Hype: {result.hype_score} · Support: {result.support_score}",
        "",
    ]
    if result.synthetic:
        lines += [
            "**FICTIONAL DEMO: observations, companies, registry rows and evidence URLs are synthetic.**",
            "",
        ]
    lines += [f"- {warning}" for warning in result.warnings] + [""]
    for s in result.signals:
        lines += [
            f"## {s.label}",
            "",
            f"Score: {s.score if s.has_data else 'No data'} · Weight: {s.weight} · {s.window}",
            f"Carried: {s.carried}",
            "",
            s.explanation,
            "",
            f"Rule: {s.rule}",
            "",
            "Inputs: " + json.dumps(s.inputs, ensure_ascii=False),
            "",
        ]
        lines += [
            f"- [{e.title.replace('[', '').replace(']', '')}]({e.url}) · {e.source} · {e.published_at or 'Date unavailable'}"
            + (f" · {e.promoter.name}: {e.promoter.status}; {e.promoter.note}" if e.promoter else "")
            for e in s.evidence
        ]
        lines.append("")
    return "\n".join(lines)


def create_app(settings: Settings | None = None) -> FastAPI:
    service = Service(settings or Settings())
    app = FastAPI(
        title="PumpWatch",
        version="0.1.0",
        description=DISCLAIMER,
        telemetry={"auto_configure": False, "tracing": False, "metrics": False, "logs": False},
    )
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/api/health", response_model=Health)
    def health():
        return Health(
            status="ok",
            mode=service.settings.mode,
            credits_spent_this_month=service.store.spend(),
            credit_budget=service.settings.monthly_budget,
            credits_spent_this_hour=service.store.spend(hours=1),
            hourly_credit_budget=service.settings.hourly_budget,
            credit_accounting="Conservative local estimate; verify billed spend in SerpApi dashboard.",
            fixture_tickers=service.resolver.examples,
            fixture_provenance=service.cache.manifest["provenance"],
            registry_ready=Registry(service.settings.data_dir).ready,
            disclaimer=DISCLAIMER,
        )

    @app.post("/api/resolve", response_model=list[Ticker])
    async def resolve(request: QueryRequest):
        candidates = await service.resolver.resolve(request.query)
        if not candidates:
            raise HTTPException(404, "No Indian stock found for that query")
        return candidates

    @app.post("/api/analyse", response_model=Analysis)
    async def analyse(request: TickerRequest):
        return await service.analyse(request.symbol, request.exchange)

    @app.get("/api/searches", response_model=list[PastSearch])
    def searches(limit: int = Query(50, ge=1, le=100)):
        return service.store.past_searches(limit)

    def require_run(run_id: str) -> Analysis:
        result = service.store.run(run_id)
        if not result:
            raise HTTPException(404, "Run not found")
        return result

    @app.get("/api/runs/{run_id}", response_model=Analysis)
    def run(run_id: str):
        return require_run(run_id)

    @app.get("/api/runs/{run_id}/calls", response_model=list[Call])
    def calls(run_id: str):
        require_run(run_id)
        return service.store.calls(run_id)

    @app.get("/api/runs/{run_id}/export")
    def export(run_id: str, format: Literal["json", "md"] = "json"):
        result = require_run(run_id)
        payload = result.model_dump()
        payload["calls"] = [c.model_dump() for c in service.store.calls(run_id)]
        body = (
            json.dumps(payload, indent=2, ensure_ascii=False) if format == "json" else markdown_report(result)
        )
        return Response(
            body,
            media_type="application/json" if format == "json" else "text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="pumpwatch-{result.ticker.symbol}.{format}"'
            },
        )

    @app.get("/api/tickers/{symbol}/history", response_model=list[HistoryPoint])
    def history(symbol: str, exchange: Literal["NSE", "BOM"] = "NSE", days: int = Query(30, ge=1, le=365)):
        return service.store.history(f"{symbol.upper()}:{exchange}", days)

    @app.get("/api/tickers/{symbol}/latest", response_model=Analysis)
    def latest(symbol: str, exchange: Literal["NSE", "BOM"] = "NSE"):
        result = service.store.latest(f"{symbol.upper()}:{exchange}")
        if not result:
            raise HTTPException(404, "No analysis yet. Search this ticker to begin.")
        return result

    @app.get("/api/watchlist", response_model=list[WatchItem])
    def watchlist():
        return service.store.watchlist()

    @app.post("/api/watchlist", response_model=list[WatchItem])
    async def add_watchlist(request: TickerRequest):
        ticker = await service.resolver.get(request.symbol, request.exchange)
        service.store.upsert_ticker(ticker, True)
        return service.store.watchlist()

    @app.delete("/api/watchlist", response_model=list[WatchItem])
    def remove_watchlist(request: TickerRequest):
        ticker = service.store.ticker(f"{request.symbol.upper()}:{request.exchange}")
        if ticker:
            service.store.upsert_ticker(ticker, False)
        return service.store.watchlist()

    @app.post("/api/snapshot", response_model=SnapshotResponse)
    async def snapshot(request: SnapshotRequest | None = None):
        return await service.snapshot(
            request.symbol if request else None, request.exchange if request else "NSE"
        )

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return Response(
            "PumpWatch API is running. Build frontend with pnpm --dir frontend build. API docs: /docs",
            media_type="text/plain",
        )

    return app
