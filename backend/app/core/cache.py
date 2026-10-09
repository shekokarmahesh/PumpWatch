import asyncio
import hashlib
import json
import random
import time
from pathlib import Path
from uuid import uuid4

import serpapi

from .config import Settings
from .models import Call
from .store import BudgetExceeded, Store, utcnow


def params_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f".{uuid4().hex}.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def redact(data, secret: str = ""):
    if isinstance(data, dict):
        return {k: redact(v, secret) for k, v in data.items() if k not in {"api_key", "SERPAPI_KEY"}}
    if isinstance(data, list):
        return [redact(v, secret) for v in data]
    if isinstance(data, str) and secret:
        return data.replace(secret, "REDACTED")
    return data


def no_results(raw: dict) -> bool:
    message = str(raw.get("error", "")).casefold()
    return "hasn't returned any results" in message or "has not returned any results" in message


class Cache:
    def __init__(self, settings: Settings, store: Store):
        self.settings, self.store = settings, store
        self.manifest = json.loads((settings.data_dir / "fixtures" / "manifest.json").read_text())
        self.semaphore = asyncio.Semaphore(4)
        self.locks: dict[str, asyncio.Lock] = {}

    async def fetch(
        self, params: dict, run_id: str, deadline: float, *, request_timeout: float = 12
    ) -> tuple[dict, Call]:
        key = params_hash(params)
        call = Call(
            id=uuid4().hex,
            engine=params["engine"],
            params=params,
            params_hash=key,
            mode="replay" if self.settings.mode == "replay" else "live",
            cache_hit=False,
            credits_spent=0,
            raw_path=None,
            fetched_at=utcnow(),
            status="pending",
        )
        async with self.locks.setdefault(key, asyncio.Lock()):
            try:
                if self.settings.mode == "replay":
                    entry = self.manifest["responses"].get(key)
                    if entry is None:
                        raise ValueError("No bundled fixture for these parameters")
                    path = self.settings.data_dir / "fixtures" / entry["path"]
                    raw = json.loads(path.read_text())
                    call.mode, call.cache_hit, call.synthetic = "replay", True, entry.get("synthetic", False)
                    call.fetched_at = entry["captured_at"]
                else:
                    path = self.settings.state_dir / "cache" / f"{key}.json"
                    cached = json.loads(path.read_text()) if path.exists() else None
                    # Even live mode reuses a response for 24 hours to protect the free-plan budget.
                    if (
                        cached is not None
                        and time.time() - path.stat().st_mtime < 86400
                        and (not cached.get("error") or no_results(cached))
                    ):
                        raw = cached
                        call.mode, call.cache_hit = "cache", True
                        call.fetched_at = raw.get("_pumpwatch_fetched_at", utcnow())
                    else:
                        if not self.settings.api_key:
                            raise ValueError("Set SERPAPI_KEY locally to use live data")
                        async with self.semaphore:
                            call.credits_spent = 1
                            self.store.reserve(
                                run_id, call, self.settings.monthly_budget, self.settings.hourly_budget
                            )
                            raw = await self._request(params, deadline, request_timeout=request_timeout)
                            raw = redact(dict(raw), self.settings.api_key)
                            raw["_pumpwatch_fetched_at"] = utcnow()
                            # Raw payload is persisted before the collector can parse it.
                            write_json(path, raw)
                call.raw_path, call.status = str(path), "success"
                if raw.get("error"):
                    if no_results(raw):
                        call.status, call.error = "empty", "The provider returned no results for this query."
                    else:
                        call.status, call.error = "error", "SerpApi returned an error response"
                    raw = {}
            except Exception as exc:
                call.status = "error"
                call.error = (
                    str(exc) if isinstance(exc, ValueError) else "Collection failed; signal unavailable"
                )
                if isinstance(exc, serpapi.TimeoutError):
                    call.error = "The provider request timed out; this signal is unavailable."
                # Unknown transport failures remain conservatively reserved as one credit.
                if isinstance(exc, (serpapi.HTTPError, BudgetExceeded)):
                    call.credits_spent = 0
                raw = {}
            self.store.save_call(run_id, call)
            return raw, call

    async def _request(self, params: dict, deadline: float, *, request_timeout: float = 12):
        for attempt in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0.2:
                raise ValueError("Analysis time budget reached")
            try:

                def search(timeout=min(request_timeout, remaining)):
                    client = serpapi.Client(api_key=self.settings.api_key, timeout=timeout)
                    return client.search(params)

                return await asyncio.to_thread(search)
            except serpapi.HTTPError as exc:
                if exc.status_code != 429 or attempt == 2:
                    raise
                delay = 2**attempt + random.uniform(0, 0.25)
                if time.monotonic() + delay >= deadline:
                    raise
                await asyncio.sleep(delay)
        raise ValueError("Collector retries exhausted")
