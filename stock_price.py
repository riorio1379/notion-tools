"""
stock_price.py
保有銘柄の株価を自動取得してNotionの株価履歴DBに記録するスクリプト
"""

import json
import os
import urllib.request
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

import yfinance as yf

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")

# 株価履歴DB（1行/日の構造化DB）
PRICE_HISTORY_DB_ID = "338972dc-26e6-817d-914d-ffbbe4a0dc4b"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

HOLDINGS = {
    "NVDA":  {"name": "Nvidia",       "shares": 26.86352324},
    "CRWV":  {"name": "CoreWeave",    "shares": 8.0},
    "BYDDY": {"name": "BYD ADR",      "shares": 36.0},
    "NTDOY": {"name": "Nintendo ADR", "shares": 21.0},
}

GBP_USD_FALLBACK = 1.29


def fetch_gbp_usd():
    try:
        t = yf.Ticker("GBPUSD=X")
        hist = t.history(period="1d")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 4)
    except:
        pass
    return GBP_USD_FALLBACK


def fetch_prices():
    result = {}
    for ticker in HOLDINGS:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                price = round(hist["Close"].iloc[-1], 2)
                prev  = round(hist["Close"].iloc[-2], 2) if len(hist) > 1 else price
                change_pct = round((price - prev) / prev * 100, 2)
                result[ticker] = {"price": price, "change_pct": change_pct}
                print(f"  {ticker}: ${price} ({'+' if change_pct >= 0 else ''}{change_pct}%)")
        except Exception as e:
            print(f"  {ticker}: 取得失敗 ({e})")
    return result


def save_to_price_history_db(prices, gbp_usd):
    """株価履歴DBに1行追加（日付・各銘柄株価・合計評価額）"""
    today = datetime.now().strftime("%Y-%m-%d")

    total_gbp = 0
    props = {
        "日付": {"title": [{"text": {"content": today}}]},
        "GBP/USD": {"number": gbp_usd},
    }

    for ticker, info in HOLDINGS.items():
        if ticker not in prices:
            continue
        price_usd = prices[ticker]["price"]
        price_gbp = price_usd / gbp_usd
        value_gbp = round(price_gbp * info["shares"], 2)
        total_gbp += value_gbp
        props[f"{ticker} ($)"] = {"number": price_usd}

    props["合計評価額 (£)"] = {"number": round(total_gbp, 2)}

    payload = {"parent": {"database_id": PRICE_HISTORY_DB_ID}, "properties": props}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data, headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    return result.get("url", ""), round(total_gbp, 2)


def print_report(prices, gbp_usd):
    print(f"\n=== レポート ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print(f"GBP/USD: {gbp_usd}")
    total_gbp = 0
    for ticker, info in HOLDINGS.items():
        if ticker not in prices:
            continue
        p = prices[ticker]
        price_usd = p["price"]
        price_gbp = round(price_usd / gbp_usd, 2)
        shares = info["shares"]
        value_gbp = round(price_gbp * shares, 2)
        total_gbp += value_gbp
        sign = "+" if p["change_pct"] >= 0 else ""
        print(f"  {ticker} ({info['name']}): ${price_usd} ({sign}{p['change_pct']}%) | {shares}株 | 評価額£{value_gbp}")
    print(f"\n  合計評価額: £{round(total_gbp, 2)}")
    return round(total_gbp, 2)


def run():
    print("=== 株価取得中 ===")
    gbp_usd = fetch_gbp_usd()
    print(f"GBP/USD: {gbp_usd}")
    prices = fetch_prices()
    print_report(prices, gbp_usd)
    url, total = save_to_price_history_db(prices, gbp_usd)
    print(f"\n株価履歴DB保存完了: {url}")
    return prices


if __name__ == "__main__":
    run()
