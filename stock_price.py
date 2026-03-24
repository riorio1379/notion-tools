"""
stock_price.py
保有銘柄の株価を自動取得してNotionの銘柄分析DBに記録するスクリプト
"""

import json
import os
import urllib.request
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

import yfinance as yf

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DB_ID = "329972dc-26e6-8110-ad76-c986f89b4421"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

HOLDINGS = {
    "CRCL":  {"name": "Circle",        "shares": 43.40, "avg_gbp": 129.15},
    "NVDA":  {"name": "Nvidia",        "shares": 0,     "avg_gbp": 0},
    "CRWV":  {"name": "CoreWeave",     "shares": 0,     "avg_gbp": 0},
    "BYDDY": {"name": "BYD ADR",       "shares": 0,     "avg_gbp": 0},
    "NTDOY": {"name": "Nintendo ADR",  "shares": 0,     "avg_gbp": 0},
}

GBP_USD = 1.29  # 手動更新 or 自動取得で更新


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


def fetch_gbp_usd():
    try:
        t = yf.Ticker("GBPUSD=X")
        hist = t.history(period="1d")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 4)
    except:
        pass
    return GBP_USD


def create_price_report(prices, gbp_usd):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nGBP/USD: {gbp_usd}\n"]

    total_value_gbp = 0
    for ticker, info in HOLDINGS.items():
        if ticker not in prices:
            continue
        p = prices[ticker]
        price_usd = p["price"]
        price_gbp = round(price_usd / gbp_usd, 2)
        shares = info["shares"]
        value_gbp = round(price_gbp * shares, 2) if shares > 0 else 0
        avg = info["avg_gbp"]
        pnl = round((price_gbp - avg) * shares, 2) if shares > 0 and avg > 0 else 0
        total_value_gbp += value_gbp

        line = f"{ticker} ({info['name']}): ${price_usd} ({'+' if p['change_pct'] >= 0 else ''}{p['change_pct']}%)"
        if shares > 0:
            line += f" | {shares}株 | 評価額£{value_gbp} | 損益£{pnl}"
        lines.append(line)

    if total_value_gbp > 0:
        lines.append(f"\n合計評価額: £{round(total_value_gbp, 2)}")

    return "\n".join(lines)


def post_to_notion(report_text):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = report_text.strip().split("\n")
    children = []
    for line in lines:
        if line.strip():
            children.append({"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"text": {"content": line}}]
            }})

    payload = {
        "parent": {"database_id": DB_ID},
        "properties": {
            "銘柄名": {"title": [{"text": {"content": f"株価レポート {today}"}}]},
        },
        "children": children
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data, headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    return result["url"]


def run():
    print("=== 株価取得中 ===")
    gbp_usd = fetch_gbp_usd()
    print(f"GBP/USD: {gbp_usd}")
    prices = fetch_prices()
    report = create_price_report(prices, gbp_usd)
    print("\n=== レポート ===")
    print(report)
    url = post_to_notion(report)
    print(f"\nNotion保存完了: {url}")
    return report


if __name__ == "__main__":
    run()
