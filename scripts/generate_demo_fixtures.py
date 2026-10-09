"""Generate fictional SerpApi-shaped scenarios, never labelled as live captures."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "fixtures"
AS_OF = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


def hashed(params):
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "as_of": AS_OF.isoformat(),
        "provenance": "Synthetic fictional scenarios generated on 2026-10-08; not market captures.",
        "tickers": [],
        "responses": {},
    }
    scenarios = [
        (
            "PULSE",
            "NSE",
            "Pulse Components",
            True,
            15,
            2,
            6,
            5,
            3,
            65,
            4,
            0,
            False,
            ["Rocket Tips", "Target Club"],
        ),
        (
            "ASTER",
            "NSE",
            "Aster Industries",
            False,
            9,
            4,
            3,
            2,
            1,
            18,
            1.7,
            1,
            False,
            ["Target Club", "Measured Markets"],
        ),
        (
            "NORTHSTAR",
            "NSE",
            "Northstar Systems",
            False,
            2,
            6,
            1.1,
            0,
            0,
            4,
            1.1,
            4,
            True,
            ["Measured Markets", "Steady Research"],
        ),
        (
            "ORBIT",
            "BOM",
            "Orbit Consumer",
            False,
            1,
            4,
            0.8,
            0,
            0,
            -2,
            0.9,
            3,
            True,
            ["Measured Markets", "Steady Research"],
        ),
        ("SPARROW", "BOM", "Sparrow Materials", True, 0, 0, 0, 1, 0, 5, 1, 0, None, []),
    ]
    for (
        symbol,
        exchange,
        name,
        sme,
        v30,
        old,
        spike,
        tips,
        ads,
        ret,
        volume,
        outlets,
        positive,
        promoters,
    ) in scenarios:
        ticker = {
            "symbol": symbol,
            "exchange": exchange,
            "company_name": name,
            "is_sme": sme,
            "listing_verified": False,
            "synthetic": True,
        }
        manifest["tickers"].append(ticker)
        stem = symbol.casefold()

        def save(params, payload):
            key = hashed(params)
            filename = f"{stem}-{params['engine']}-{key[:8]}.json"
            metadata = {"status": "Success", "created_at": AS_OF.isoformat()}
            raw = {
                "search_parameters": params,
                "search_metadata": metadata,
                "_pumpwatch_fetched_at": AS_OF.isoformat(),
                "_pumpwatch_synthetic": True,
                **payload,
            }
            (OUTPUT / filename).write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
            manifest["responses"][key] = {
                "path": filename,
                "params": params,
                "captured_at": AS_OF.isoformat(),
                "synthetic": True,
            }

        for window, count in [("1M", 30), ("1Y", 365)]:
            graph = [
                {
                    "date": (AS_OF - timedelta(days=count - i - 1)).isoformat(),
                    "price": round(100 * (1 + ret / 100 * i / (count - 1)), 2),
                    "volume": 10000 * (volume if window == "1M" else 1),
                }
                for i in range(count)
            ]
            financials = (
                []
                if positive is None
                else [
                    {
                        "title": "Income Statement",
                        "results": [
                            {
                                "date": dt,
                                "period_type": "Quarterly",
                                "table": [
                                    {
                                        "title": "Revenue",
                                        "value": str((100 + i * (20 if positive else -10)) * 1000000),
                                    },
                                    {"title": "Net income", "value": str((10 if positive else -5) * 1000000)},
                                ],
                            }
                            for i, dt in enumerate(["Sep 2025", "Dec 2025", "Mar 2026", "Jun 2026"])
                        ],
                    }
                ]
            )
            save(
                {"engine": "google_finance", "q": f"{symbol}:{exchange}", "window": window, "hl": "en"},
                {
                    "summary": {
                        "title": name,
                        "stock": symbol,
                        "exchange": exchange,
                        "extracted_price": graph[-1]["price"],
                    },
                    "graph": graph,
                    "financials": financials,
                },
            )
        videos = []
        for group, count in [("recent", v30), ("baseline", old)]:
            for i in range(count):
                videos.append(
                    {
                        "title": f"{name}: {'target update' if i % 2 else 'multibagger breakout'} · demo {i + 1}",
                        "published_date": (
                            AS_OF - timedelta(days=(i + 1 if group == "recent" else 40 + i))
                        ).isoformat(),
                        "link": f"https://example.com/pumpwatch/{stem}/video/{group}-{i}",
                        "channel": {"name": promoters[i % len(promoters)]},
                        "views": 1200 * (i + 1),
                    }
                )
        if not v30 and positive is not None:
            videos.append(
                {
                    "title": name + " annual report discussion",
                    "published_date": (AS_OF - timedelta(days=4)).isoformat(),
                    "link": f"https://example.com/pumpwatch/{stem}/video/annual",
                    "channel": {"name": "Measured Markets"},
                }
            )
        save(
            {"engine": "youtube", "search_query": name + " target", "sp": "EgIIBA=="},
            {"video_results": videos[:v30]},
        )
        save(
            {"engine": "youtube", "search_query": name + " target", "sp": "EgIIBQ=="},
            {"video_results": videos},
        )
        timeline = (
            [
                {
                    "date": (AS_OF - timedelta(weeks=52 - i)).date().isoformat(),
                    "timestamp": str(int((AS_OF - timedelta(weeks=52 - i)).timestamp())),
                    "values": [
                        {
                            "query": name,
                            "value": str(10 if i < 48 else 10 * spike),
                            "extracted_value": 10 if i < 48 else 10 * spike,
                        }
                    ],
                }
                for i in range(52)
            ]
            if spike
            else []
        )
        save(
            {
                "engine": "google_trends",
                "q": name,
                "geo": "IN",
                "data_type": "TIMESERIES",
                "date": "today 12-m",
            },
            {"interest_over_time": {"timeline_data": timeline}},
        )
        organic = [
            {
                "title": f"{name} target · demo indexed group {i + 1}",
                "snippet": "Fictional buy call for demonstrating the parser.",
                "link": f"https://t.me/pumpwatch_fictional_{stem}_{i}",
                "date": (AS_OF - timedelta(days=3 + i)).isoformat(),
            }
            for i in range(tips)
        ]
        # Controls include observed results without tip keywords, so observed zero differs from empty/no data.
        if not tips:
            organic = [
                {
                    "title": name + " company information",
                    "snippet": "Fictional neutral sample",
                    "link": f"https://example.com/{stem}",
                    "date": AS_OF.isoformat(),
                }
            ]
        save(
            {
                "engine": "google",
                "q": f'"{name}" (target OR multibagger OR "buy call") (site:t.me OR site:whatsapp.com OR site:chat.whatsapp.com)',
                "gl": "in",
                "hl": "en",
                "tbs": "qdr:m",
            },
            {"organic_results": organic},
        )
        domains = ["moneycontrol.com", "livemint.com", "reuters.com", "business-standard.com"]
        news = [
            {
                "title": f"{name}: fictional quarterly results sample",
                "source": {"name": domain, "url": "https://" + domain},
                "link": f"https://example.com/pumpwatch/{stem}/news/{i}",
                "iso_date": (AS_OF - timedelta(days=4)).isoformat(),
            }
            for i, domain in enumerate(domains[:outlets])
        ]
        if not outlets and positive is not None:
            news = [
                {
                    "title": name + " fictional local update",
                    "source": {"name": "Demo Blog", "url": "https://example.com"},
                    "link": f"https://example.com/pumpwatch/{stem}/news/blog",
                    "iso_date": AS_OF.isoformat(),
                }
            ]
        save({"engine": "google_news", "q": name, "gl": "in", "hl": "en"}, {"news_results": news})
        creatives = [
            {
                "title": name + " target workshop · fictional creative",
                "advertiser": promoters[i % len(promoters)],
                "ad_creative_id": f"DEMO{i}",
                "format": "text",
                "first_shown": int((AS_OF - timedelta(days=15)).timestamp()),
                "last_shown": int(AS_OF.timestamp()),
                "details_link": f"https://example.com/pumpwatch/{stem}/ad/{i}",
            }
            for i in range(ads)
        ]
        save(
            {"engine": "google_ads_transparency_center", "text": name, "region": "2356"},
            {"ad_creatives": creatives},
        )
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
