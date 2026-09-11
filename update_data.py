#!/usr/bin/env python3
"""Fetch keyless public market data and write data.json.

Uses Yahoo Finance's public chart endpoint (no API key). The endpoint is unofficial
and can change; failures keep the previous value when possible so the dashboard
still renders.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data.json"

MARKETS = [
    ("usdkrw", "KRW=X", "USD/KRW", "원", "환율"),
    ("usdjpy", "JPY=X", "USD/JPY", "엔", "환율"),
    ("sp500", "^GSPC", "S&P 500", "", "미국"),
    ("nasdaq", "^IXIC", "NASDAQ", "", "미국"),
    ("sox", "^SOX", "PHLX 반도체", "", "반도체"),
    ("kospi", "^KS11", "KOSPI", "", "한국"),
    ("kosdaq", "^KQ11", "KOSDAQ", "", "한국"),
    ("gold", "GC=F", "Gold", "$", "원자재"),
    ("silver", "SI=F", "Silver", "$", "원자재"),
    ("hstech", "^HSTECH", "Hang Seng TECH", "", "중국"),
]

ETFS = [
    ("381180", "381180.KS", "TIGER 미국필라델피아반도체나스닥", "반도체"),
    ("458730", "458730.KS", "TIGER 미국배당다우존스", "배당"),
    ("486290", "486290.KS", "TIGER 미국나스닥100타겟데일리커버드콜", "커버드콜"),
    ("0046Y0", "0046Y0.KS", "ACE 미국배당퀄리티", "배당"),
    ("360750", "360750.KS", "TIGER 미국S&P500", "S&P500"),
    ("0041E0", "0041E0.KS", "KODEX 미국S&P500액티브", "S&P500 액티브"),
    ("0066W0", "0066W0.KS", "SOL 국제금", "금"),
    ("494890", "494890.KS", "KODEX 200액티브", "한국"),
    ("0043Y0", "0043Y0.KS", "TIME 차이나AI테크액티브", "중국 AI"),
    ("0172V0", "0172V0.KS", "1Q 은액티브", "은"),
]


def load_old() -> dict:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"markets": {}, "etfs": {}}


def fetch_json(url: str, timeout: int = 15) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (a / b - 1) * 100


def nearest_past(points, seconds_back: int):
    if not points:
        return None
    target = points[-1][0] - seconds_back
    candidates = [p for p in points if p[0] <= target]
    return candidates[-1][1] if candidates else points[0][1]


def fetch_symbol(symbol: str) -> dict:
    # 1y daily is enough for 1D / 7D / 30D / 52w range and sparklines.
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + quote(symbol, safe="")
        + "?range=1y&interval=1d&includePrePost=false&events=div%2Csplits"
    )
    payload = fetch_json(url)
    result = payload["chart"]["result"][0]
    ts = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_data.get("close") or []
    points = []
    for t, c in zip(ts, closes):
        if c is not None and isinstance(c, (int, float)) and math.isfinite(c):
            points.append((int(t), float(c)))
    if len(points) < 2:
        raise RuntimeError(f"Not enough data for {symbol}")

    last = points[-1][1]
    prev = points[-2][1]
    one_week = nearest_past(points, 7 * 86400)
    one_month = nearest_past(points, 30 * 86400)
    year_vals = [p[1] for p in points]
    last90 = points[-90:]

    return {
        "symbol": symbol,
        "price": last,
        "day_pct": pct(last, prev),
        "week_pct": pct(last, one_week),
        "month_pct": pct(last, one_month),
        "year_low": min(year_vals),
        "year_high": max(year_vals),
        "history": [
            {
                "date": datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                "close": round(c, 6),
            }
            for t, c in last90
        ],
        "source_updated_at": datetime.fromtimestamp(points[-1][0], tz=timezone.utc).isoformat(),
        "fresh": True,
    }


def merge_fetch(old_section: dict, key: str, symbol: str) -> dict:
    try:
        data = fetch_symbol(symbol)
        time.sleep(0.18)
        return data
    except Exception as e:
        fallback = dict(old_section.get(key) or {})
        if fallback:
            fallback["fresh"] = False
            fallback["error"] = str(e)[:180]
            return fallback
        return {
            "symbol": symbol,
            "price": None,
            "day_pct": None,
            "week_pct": None,
            "month_pct": None,
            "year_low": None,
            "year_high": None,
            "history": [],
            "fresh": False,
            "error": str(e)[:180],
        }


def main():
    old = load_old()
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets": {},
        "etfs": {},
        "derived": {},
        "manual_funds": [
            "한국투자 MySuper 알아서성장형",
            "삼성 글로벌밸런드",
            "유리 필라델피아반도체인덱스",
        ],
    }

    for key, symbol, name, unit, category in MARKETS:
        d = merge_fetch(old.get("markets", {}), key, symbol)
        d.update({"name": name, "unit": unit, "category": category})
        output["markets"][key] = d

    for code, symbol, name, category in ETFS:
        d = merge_fetch(old.get("etfs", {}), code, symbol)
        d.update({"code": code, "name": name, "category": category, "unit": "원"})
        output["etfs"][code] = d

    # 100 JPY in KRW, derived from USD/KRW and USD/JPY.
    krw = output["markets"].get("usdkrw", {}).get("price")
    jpy = output["markets"].get("usdjpy", {}).get("price")
    if krw and jpy:
        output["derived"]["jpykrw100"] = {
            "name": "100 JPY/KRW",
            "price": krw / jpy * 100,
            "unit": "원",
        }

    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
