#!/usr/bin/env python3
"""Build data.json for PANG INVEST DAILY with keyless public Naver Finance data.

No API keys are used. Korean ETFs/indices and foreign indices use Naver's
public chart endpoints. FX and metals use Naver's public market-index endpoints.
If one source temporarily fails, the last saved value is kept when possible.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data.json"

ETFS = [
    ("381180", "TIGER 미국필라델피아반도체나스닥", "반도체"),
    ("458730", "TIGER 미국배당다우존스", "배당"),
    ("486290", "TIGER 미국나스닥100타겟데일리커버드콜", "커버드콜"),
    ("0046Y0", "ACE 미국배당퀄리티", "배당"),
    ("360750", "TIGER 미국S&P500", "S&P500"),
    ("0041E0", "KODEX 미국S&P500액티브", "S&P500 액티브"),
    ("0066W0", "SOL 국제금", "금"),
    ("494890", "KODEX 200액티브", "한국"),
    ("0043Y0", "TIME 차이나AI테크액티브", "중국 AI"),
    ("0172V0", "1Q 은액티브", "은"),
]

FOREIGN_INDEXES = {
    "sp500": (".INX", "S&P 500", "", "미국"),
    "nasdaq": (".IXIC", "NASDAQ", "", "미국"),
    "sox": (".SOX", "PHLX 반도체", "", "반도체"),
}

DOMESTIC_INDEXES = {
    "kospi": ("KOSPI", "KOSPI", "", "한국"),
    "kosdaq": ("KOSDAQ", "KOSDAQ", "", "한국"),
}


def load_old() -> dict:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"markets": {}, "etfs": {}, "derived": {}}


def fetch_json(url: str, timeout: int = 20):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://m.stock.naver.com/",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        },
    )
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def to_num(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    s = str(value).strip().replace(",", "").replace("%", "")
    if not s or s in {"-", "--", "N/A", "null", "None"}:
        return None
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (a / b - 1) * 100


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def date_text(value):
    s = str(value or "").replace("-", "").replace(".", "")
    if len(s) >= 8 and s[:8].isdigit():
        return s[:8]
    return None


def iso_date(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def extract_chart_points(payload):
    points = {}
    for item in walk_dicts(payload):
        d = date_text(item.get("localDate") or item.get("date") or item.get("tradeDate"))
        c = to_num(item.get("closePrice"))
        if d and c is not None:
            points[d] = c
    return sorted(points.items())


def history_stats(points, symbol):
    if not points:
        raise RuntimeError(f"No chart data for {symbol}")

    dated = [(datetime.strptime(d, "%Y%m%d").date(), c) for d, c in points]
    last_date, last = dated[-1]

    def past_price(days):
        target = last_date - timedelta(days=days)
        vals = [(d, c) for d, c in dated if d <= target]
        return vals[-1][1] if vals else None

    prev = dated[-2][1] if len(dated) >= 2 else None
    week = past_price(7)
    month = past_price(30)
    vals = [c for _, c in dated]

    return {
        "symbol": symbol,
        "price": last,
        "day_pct": pct(last, prev),
        "week_pct": pct(last, week),
        "month_pct": pct(last, month),
        "year_low": min(vals),
        "year_high": max(vals),
        "history": [
            {"date": d.isoformat(), "close": round(c, 6)}
            for d, c in dated[-90:]
        ],
        "source_updated_at": last_date.isoformat(),
        "fresh": True,
        "source": "NAVER",
    }


def fetch_domestic_chart(code: str):
    url = (
        "https://api.stock.naver.com/chart/domestic/item/"
        + quote(code, safe="")
        + "?periodType=dayCandle"
    )
    return history_stats(extract_chart_points(fetch_json(url)), code)


def fetch_domestic_index(code: str):
    url = (
        "https://api.stock.naver.com/chart/domestic/index/"
        + quote(code, safe="")
        + "?periodType=dayCandle"
    )
    return history_stats(extract_chart_points(fetch_json(url)), code)


def fetch_foreign_index(reuters_code: str):
    url = (
        "https://api.stock.naver.com/chart/foreign/index/"
        + quote(reuters_code, safe=".")
        + "?periodType=dayCandle"
    )
    return history_stats(extract_chart_points(fetch_json(url)), reuters_code)


def append_current_history(old_item: dict, price: float):
    today = datetime.now(timezone.utc).date().isoformat()
    hist = []
    for row in (old_item or {}).get("history", []):
        d, c = row.get("date"), to_num(row.get("close"))
        if d and c is not None and d != today:
            hist.append({"date": d, "close": c})
    hist.append({"date": today, "close": price})

    unique = {x["date"]: x["close"] for x in hist}
    rows = [{"date": d, "close": unique[d]} for d in sorted(unique)][-90:]
    return rows


def current_stats(old_item: dict, *, symbol: str, price: float, day_pct=None):
    history = append_current_history(old_item, price)
    dated = [(datetime.fromisoformat(x["date"]).date(), x["close"]) for x in history]
    last_date, last = dated[-1]

    def past_price(days):
        target = last_date - timedelta(days=days)
        vals = [(d, c) for d, c in dated if d <= target]
        return vals[-1][1] if vals else None

    prev = dated[-2][1] if len(dated) >= 2 else None
    vals = [c for _, c in dated]
    return {
        "symbol": symbol,
        "price": price,
        "day_pct": day_pct if day_pct is not None else pct(last, prev),
        "week_pct": pct(last, past_price(7)),
        "month_pct": pct(last, past_price(30)),
        "year_low": min(vals) if vals else price,
        "year_high": max(vals) if vals else price,
        "history": history,
        "source_updated_at": datetime.now(timezone.utc).isoformat(),
        "fresh": True,
        "source": "NAVER",
    }


def find_by_code(payload, code: str):
    code = code.upper()
    for item in walk_dicts(payload):
        for field in ("reutersCode", "symbolCode", "code"):
            if str(item.get(field, "")).upper() == code:
                return item
    return None


def find_by_name(payload, *needles):
    needles = tuple(n.lower() for n in needles)
    for item in walk_dicts(payload):
        text = " ".join(
            str(item.get(k, ""))
            for k in ("name", "indexName", "indexNameEng", "krName", "engName")
        ).lower()
        if text and all(n in text for n in needles):
            return item
    return None


def fetch_fx(old_markets: dict):
    payload = fetch_json("https://m.stock.naver.com/front-api/marketIndex/exchange/main")
    out = {}

    usd = find_by_code(payload, "FX_USDKRW") or find_by_name(payload, "미국", "usd")
    if usd:
        price = to_num(usd.get("closePrice"))
        if price is not None:
            out["usdkrw"] = current_stats(
                old_markets.get("usdkrw", {}),
                symbol="FX_USDKRW",
                price=price,
                day_pct=to_num(usd.get("fluctuationsRatio")),
            )
            out["usdkrw"].update({"name": "USD/KRW", "unit": "원", "category": "환율"})

    jpy = find_by_code(payload, "FX_JPYKRW") or find_by_name(payload, "일본", "jpy")
    if jpy:
        price = to_num(jpy.get("closePrice"))
        if price is not None:
            out["_jpykrw100"] = {
                "name": "100 JPY/KRW",
                "price": price,
                "unit": "원",
                "day_pct": to_num(jpy.get("fluctuationsRatio")),
            }

    return out


def fetch_metals(old_markets: dict):
    payload = fetch_json("https://m.stock.naver.com/front-api/marketIndex/metals")
    out = {}
    for key, code, name in (("gold", "GC", "Gold"), ("silver", "SI", "Silver")):
        item = find_by_code(payload, code)
        if not item:
            item = find_by_name(payload, "gold" if key == "gold" else "silver")
        if not item:
            item = find_by_name(payload, "금" if key == "gold" else "은")
        if item:
            price = to_num(item.get("closePrice"))
            if price is not None:
                out[key] = current_stats(
                    old_markets.get(key, {}),
                    symbol=str(item.get("reutersCode") or item.get("symbolCode") or code),
                    price=price,
                    day_pct=to_num(item.get("fluctuationsRatio")),
                )
                out[key].update({"name": name, "unit": "$", "category": "원자재"})
    return out


def fetch_hstech():
    code = None
    try:
        nation = fetch_json("https://api.stock.naver.com/index/nation/HKG")
        candidates = list(walk_dicts(nation))
        for item in candidates:
            text = " ".join(
                str(item.get(k, ""))
                for k in ("indexName", "indexNameEng", "name")
            ).lower()
            if ("tech" in text or "테크" in text) and item.get("reutersCode"):
                code = str(item["reutersCode"])
                break
    except Exception:
        pass

    candidates = [code, ".HSTECH", ".HSTECHI"]
    last_err = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            data = fetch_foreign_index(candidate)
            data.update({"name": "Hang Seng TECH", "unit": "", "category": "중국"})
            return data
        except Exception as e:
            last_err = e
    raise RuntimeError(str(last_err or "Hang Seng TECH unavailable"))


def fallback(old_section: dict, key: str, *, symbol: str, error: Exception):
    item = dict(old_section.get(key) or {})
    if item:
        item["fresh"] = False
        item["error"] = str(error)[:180]
        return item
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
        "error": str(error)[:180],
    }


def main():
    old = load_old()
    old_markets = old.get("markets", {})
    old_etfs = old.get("etfs", {})

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

    # FX current prices
    try:
        fx = fetch_fx(old_markets)
        jpy_derived = fx.pop("_jpykrw100", None)
        output["markets"].update(fx)
        if jpy_derived:
            output["derived"]["jpykrw100"] = jpy_derived
    except Exception as e:
        output["markets"]["usdkrw"] = fallback(
            old_markets, "usdkrw", symbol="FX_USDKRW", error=e
        )
        output["markets"]["usdkrw"].update({"name": "USD/KRW", "unit": "원", "category": "환율"})

    # US indices
    for key, (code, name, unit, category) in FOREIGN_INDEXES.items():
        try:
            d = fetch_foreign_index(code)
        except Exception as e:
            d = fallback(old_markets, key, symbol=code, error=e)
        d.update({"name": name, "unit": unit, "category": category})
        output["markets"][key] = d

    # Korean indices
    for key, (code, name, unit, category) in DOMESTIC_INDEXES.items():
        try:
            d = fetch_domestic_index(code)
        except Exception as e:
            d = fallback(old_markets, key, symbol=code, error=e)
        d.update({"name": name, "unit": unit, "category": category})
        output["markets"][key] = d

    # Metals
    try:
        metals = fetch_metals(old_markets)
    except Exception:
        metals = {}
    for key, name in (("gold", "Gold"), ("silver", "Silver")):
        if key in metals:
            output["markets"][key] = metals[key]
        else:
            d = fallback(old_markets, key, symbol=key.upper(), error=RuntimeError("Naver metals unavailable"))
            d.update({"name": name, "unit": "$", "category": "원자재"})
            output["markets"][key] = d

    # Hang Seng TECH
    try:
        output["markets"]["hstech"] = fetch_hstech()
    except Exception as e:
        d = fallback(old_markets, "hstech", symbol=".HSTECH", error=e)
        d.update({"name": "Hang Seng TECH", "unit": "", "category": "중국"})
        output["markets"]["hstech"] = d

    # Korean ETFs
    for code, name, category in ETFS:
        try:
            d = fetch_domestic_chart(code)
        except Exception as e:
            d = fallback(old_etfs, code, symbol=code, error=e)
        d.update({"code": code, "name": name, "category": category, "unit": "원"})
        output["etfs"][code] = d

    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
