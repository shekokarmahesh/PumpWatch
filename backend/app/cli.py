import asyncio
import csv
import json
from pathlib import Path
from typing import Annotated

import typer

from .core.cache import write_json
from .core.config import ROOT, Settings
from .core.service import Service

cli = typer.Typer(help="PumpWatch analysis, snapshots, fixtures and registry tools")


@cli.command()
def analyse(ticker: str):
    """Analyse SYMBOL:NSE or CODE:BOM; default exchange is NSE."""
    symbol, _, exchange = ticker.partition(":")
    service = Service(Settings())
    result = asyncio.run(service.analyse(symbol, exchange or "NSE"))
    typer.echo(result.model_dump_json(indent=2))


@cli.command()
def snapshot(output: Path = ROOT / "snapshots" / "latest.json"):
    """Snapshot the local watchlist once per day. No history is invented."""
    service = Service(Settings())
    result = asyncio.run(service.snapshot())
    write_json(
        output,
        {
            "mode": service.settings.mode,
            **result.model_dump(),
            "watchlist": [item.model_dump() for item in service.store.watchlist()],
        },
    )
    typer.echo(result.model_dump_json())


@cli.command("capture-fixtures")
def capture_fixtures(tickers: Annotated[list[str], typer.Argument()], output: Path):
    """Capture real raw responses and a replay manifest into a separate output folder."""
    settings = Settings(mode="cache-first")
    if not settings.api_key:
        raise typer.BadParameter("Set SERPAPI_KEY locally before capture")
    service = Service(settings)
    manifest = {"provenance": "Live SerpApi capture", "as_of": None, "tickers": [], "responses": {}}
    for key in tickers:
        symbol, _, exchange = key.partition(":")
        result = asyncio.run(service.analyse(symbol, exchange or "NSE"))
        calls = service.store.calls(result.run_id)
        if any(c.status != "success" for c in calls):
            raise typer.BadParameter(
                f"Incomplete capture for {key}; check the persisted call log before retrying"
            )
        manifest["tickers"].append(result.ticker.model_dump())
        manifest["as_of"] = result.data_as_of
        for call in calls:
            raw = json.loads(Path(call.raw_path).read_text())
            file = f"{call.params_hash}.json"
            write_json(output / file, raw)
            manifest["responses"][call.params_hash] = {
                "path": file,
                "captured_at": call.fetched_at,
                "synthetic": False,
                "params": call.params,
            }
    write_json(output / "manifest.json", manifest)
    typer.echo(
        f"Saved {len(manifest['responses'])} responses to {output}; review before replacing demo fixtures."
    )


@cli.command("refresh-registry")
def refresh_registry(
    research_analysts: Path,
    investment_advisers: Path,
    captured_at: str,
    source_url: str,
    verified_complete: bool = False,
):
    """Import manually downloaded, reviewed SEBI CSVs. No unstable scraper is used."""
    from datetime import date
    from urllib.parse import urlparse

    date.fromisoformat(captured_at)
    host = urlparse(source_url).hostname or ""
    if host not in {"sebi.gov.in", "www.sebi.gov.in"}:
        raise typer.BadParameter("Source must be an official sebi.gov.in URL")
    imports = []
    for source, kind, filename in [
        (research_analysts, "RA", "research_analysts.csv"),
        (investment_advisers, "IA", "investment_advisers.csv"),
    ]:
        rows = list(csv.DictReader(source.read_text(encoding="utf-8-sig").splitlines()))
        if not rows or any(not row.get("name") or not row.get("registration_number") for row in rows):
            raise typer.BadParameter("CSV needs nonempty name and registration_number columns")
        imports.append((filename, [{**row, "registry_type": kind} for row in rows]))
    folder = Settings().data_dir / "registry"
    for filename, rows in imports:
        with (folder / filename).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["name", "registration_number", "registry_type", "valid_until"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
    write_json(
        folder / "metadata.json",
        {"captured_at": captured_at, "source_url": source_url, "verified_complete": verified_complete},
    )
    typer.echo(
        "Registry imported. Name checks are enabled only with --verified-complete and a capture within 30 days."
    )


@cli.command("openapi")
def openapi(output: Path = ROOT / "frontend" / "openapi.json"):
    from .main import create_app

    write_json(output, create_app().openapi())
    typer.echo(str(output))


if __name__ == "__main__":
    cli()
