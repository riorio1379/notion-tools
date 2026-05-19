"""
sync_portfolio_state.py
ポートフォリオ状態の単一の真実 (holdings.json) を基準に、以下を同期する：
  1. ~/00_Important_Context/memories/02_現状_就活と投資の最新状況.md の「投資ポートフォリオ」セクション
  2. Notion 📋売買記録ページ の売買履歴一覧テーブル（--record-trade 時のみ）

設計思想：
- holdings.json をマスター・他をビューとして扱う
- 02ファイルは「投資ポートフォリオ」セクションのみ機械的に再生成（他セクションは保護）
- stock_price.py も holdings.json を読む（重複管理の排除）

使い方：
  # 02ファイルを最新の株価で再生成（売買なし・日次更新等）
  python3 sync_portfolio_state.py

  # 売買を記録し、holdings.json と02ファイルと Notion テーブルを同時更新
  python3 sync_portfolio_state.py --record-trade \\
      --ticker NVDA --action SELL --shares 10 --price 235.42 \\
      --cash-delta-gbp +1736.19 --note "決算前PARTIAL SELL"

  # 03に追記した後にこのコマンドを呼ぶ（CLAUDE.md自動記録ルール参照）
"""

import argparse
import json
import os
import re
import urllib.request
from datetime import datetime

# ====== 定数・パス ======
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOLDINGS_JSON_PATH = os.path.join(SCRIPT_DIR, "holdings.json")
MEMORY_02_PATH = os.path.expanduser("~/RIO/Memory/02_現状_就活と投資の最新状況.md")

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# 📋売買記録ページ内のテーブルブロックID（売買履歴一覧）
NOTION_TRADE_TABLE_BLOCK_ID = "338972dc-26e6-81e9-b828-e9bd0a25a48c"
NOTION_TRADE_PAGE_URL = "https://www.notion.so/338972dc26e681609b2ef091f9f1775c"

GBP_USD_FALLBACK = 1.29
TWELVE_DATA_BASE = "https://api.twelvedata.com"


# ====== holdings.json I/O ======
def load_holdings():
    with open(HOLDINGS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_holdings(data):
    with open(HOLDINGS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ====== 株価取得（stock_price.pyと同じロジック） ======
def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def fetch_gbp_usd():
    try:
        url = f"{TWELVE_DATA_BASE}/price?symbol=GBP/USD&apikey={TWELVE_DATA_API_KEY}"
        data = _get(url)
        return round(float(data["price"]), 4)
    except Exception:
        return GBP_USD_FALLBACK


def fetch_prices(tickers):
    result = {}
    if not tickers:
        return result
    symbols = ",".join(tickers)
    try:
        url = f"{TWELVE_DATA_BASE}/quote?symbol={symbols}&apikey={TWELVE_DATA_API_KEY}"
        data = _get(url)
        # Twelve Data returns a dict keyed by ticker when multiple symbols,
        # but a flat dict when only one. Normalize.
        if len(tickers) == 1:
            data = {tickers[0]: data}
        for ticker in tickers:
            try:
                q = data[ticker]
                result[ticker] = round(float(q["close"]), 2)
            except Exception:
                result[ticker] = None
    except Exception as e:
        print(f"  価格取得失敗: {e}")
    return result


# ====== 02 ファイル再生成 ======
def render_portfolio_section(holdings_data, prices, gbp_usd, today):
    """02ファイルの「## 投資ポートフォリオ（最新）」セクションをmarkdownで返す。"""
    holdings = holdings_data["holdings"]
    cash = holdings_data["cash"]

    # 保有銘柄表
    table_rows = []
    total_gbp = 0.0
    for ticker, info in holdings.items():
        shares = info["shares"]
        price = prices.get(ticker)
        if price is None:
            value_gbp = "N/A"
            price_str = "N/A"
        else:
            value = price * shares / gbp_usd
            total_gbp += value
            value_gbp = f"£{value:,.0f}"
            price_str = f"${price}"
        shares_str = f"{shares:.2f}株" if shares != int(shares) else f"{int(shares)}株"
        table_rows.append(f"| {ticker}（{info['name']}） | {shares_str} | {price_str} | {value_gbp} |")

    table_md = "\n".join(table_rows)

    # 現金行
    freetrade = cash.get("freetrade_gbp", 0)
    monzo = cash.get("monzo_isa_gbp", 0)
    jpy_oku = cash.get("mizuho_jpy_oku", 0)

    # 株式投資余力（Freetrade内・open_ordersで拘束されている分を引く）
    locked_gbp = 0.0
    for order in holdings_data.get("open_orders", []):
        if order.get("currency") == "GBP" and order.get("locked_amount"):
            locked_gbp += order["locked_amount"]
    available_gbp = freetrade - locked_gbp

    # 注文・クローズ済みポジションのコメント文
    notes = []
    for closed in holdings_data.get("closed_positions_log", []):
        pnl = closed.get("realized_pnl_gbp")
        pnl_str = f"実現損益 £{pnl:+,}" if pnl is not None else "実現損益記録なし"
        notes.append(
            f"- {closed['ticker']}：{closed['closed_date']}に{closed['shares']}株売却済み（{pnl_str}・{closed['note']}）"
        )
    for order in holdings_data.get("open_orders", []):
        notes.append(
            f"- {order['ticker']}：{order.get('action','?')} {order.get('limit_price','?')} 注文中（{order.get('note','')}）"
        )

    closed_block = "\n".join(notes) if notes else "- （クローズ済みポジション・未執行注文なし）"

    last_trade = holdings_data.get("last_trade_ref", "（記録なし）")

    section = f"""## 投資ポートフォリオ（最新）

> ⚙️ このセクションは `sync_portfolio_state.py` が自動生成しています。手で編集しないでください（次回sync時に上書きされます）。
> ソース：[holdings.json](../automation/holdings.json) / 直近の売買：{last_trade}

### 保有銘柄・株数（{today}時点・ライブ価格）
| 銘柄 | 株数 | 直近株価 | 評価額(£) |
|------|------|----------|-----------|
{table_md}
| **合計** | | | **£{total_gbp:,.0f}** |

- GBP/USD: {gbp_usd}（{today}取得）

### クローズ済みポジション・未執行注文
{closed_block}

### 現金残高・口座構造（{today}時点）
- Freetrade口座内：約£{freetrade:,.0f} ← 株式投資に使える資金{f"（うち£{locked_gbp:,.0f}は指値拘束中）" if locked_gbp > 0 else ""}
- Monzo ISAポット：£{monzo:,.0f}　← 年利3.15%で運用中・株式投資には使わない
- みずほ銀行（日本円）：{jpy_oku}万円以上　← 生活防衛資金（円建て）
- **株式投資余力：約£{available_gbp:,.0f}**

### Notionツール
- 株価履歴DB：338972dc-26e6-817d-914d-ffbbe4a0dc4b（stock_price.pyが日次1行記録）
- 📋 売買記録ページ：{NOTION_TRADE_PAGE_URL}
- 銘柄分析DB：329972dc-26e6-8110-ad76-c986f89b4421（思考プロセスページ含む・削除禁止）
"""
    return section


def update_memory_02(holdings_data, prices, gbp_usd):
    """02ファイルの「## 投資ポートフォリオ」セクションのみ書き換える。"""
    today = datetime.now().strftime("%Y-%m-%d")
    new_section = render_portfolio_section(holdings_data, prices, gbp_usd, today)

    with open(MEMORY_02_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 「## 投資ポートフォリオ」から次の「---」までを置換
    pattern = re.compile(
        r"## 投資ポートフォリオ.*?(?=\n---\n)",
        flags=re.DOTALL,
    )
    if not pattern.search(content):
        raise RuntimeError("02ファイルに「## 投資ポートフォリオ」セクションが見つかりません")

    new_content = pattern.sub(new_section.rstrip() + "\n", content)

    # 「最終更新:」行も今日に同期
    new_content = re.sub(
        r"^最終更新:.*$",
        f"最終更新: {today}",
        new_content,
        count=1,
        flags=re.MULTILINE,
    )

    with open(MEMORY_02_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ 02ファイル更新完了: {MEMORY_02_PATH}")


# ====== Notion 売買履歴一覧テーブル追記 ======
def append_notion_trade_row(date_str, ticker, action_jp, price_usd, shares, realized_pnl_gbp, note):
    """Notion 📋売買記録ページの「売買履歴一覧」テーブルに1行追加する。"""
    pnl_str = "—" if realized_pnl_gbp is None else f"£{realized_pnl_gbp:+,}"

    def cell(text):
        return [{"type": "text", "text": {"content": str(text)}}]

    row = {
        "object": "block",
        "type": "table_row",
        "table_row": {
            "cells": [
                cell(date_str),
                cell(ticker),
                cell(action_jp),
                cell(f"${price_usd}"),
                cell(f"{shares}"),
                cell(pnl_str),
                cell(note),
            ]
        },
    }

    payload = {"children": [row]}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{NOTION_TRADE_TABLE_BLOCK_ID}/children",
        data=data,
        headers=NOTION_HEADERS,
        method="PATCH",
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    print(f"✅ Notion売買履歴テーブルに行追加: {date_str} {ticker} {action_jp}")
    return result


# ====== 売買記録（holdings.jsonの株数・現金更新） ======
def record_trade(ticker, action, shares, price, cash_delta_gbp, note):
    """holdings.json に売買を反映する。"""
    holdings_data = load_holdings()
    holdings = holdings_data["holdings"]

    if ticker not in holdings:
        # 新規銘柄
        if action != "BUY":
            raise ValueError(f"未保有銘柄 {ticker} を SELL できません")
        holdings[ticker] = {"name": ticker, "shares": 0.0}

    delta = shares if action == "BUY" else -shares
    new_shares = holdings[ticker]["shares"] + delta
    if new_shares < -1e-6:
        raise ValueError(f"{ticker}: 売却株数 {shares} > 保有株数 {holdings[ticker]['shares']}")

    if abs(new_shares) < 1e-6:
        # 全株売却 → closed_positions_log に移して holdings から削除
        closed = holdings_data.setdefault("closed_positions_log", [])
        closed.append({
            "ticker": ticker,
            "closed_date": datetime.now().strftime("%Y-%m-%d"),
            "shares": shares,
            "realized_pnl_gbp": None,
            "note": note or f"全株売却 @ ${price}",
        })
        del holdings[ticker]
    else:
        holdings[ticker]["shares"] = round(new_shares, 8)

    # 現金更新
    holdings_data["cash"]["freetrade_gbp"] = round(
        holdings_data["cash"].get("freetrade_gbp", 0) + cash_delta_gbp, 2
    )

    # メタ
    today = datetime.now().strftime("%Y-%m-%d")
    holdings_data["last_updated"] = today
    holdings_data["last_trade_ref"] = (
        f"{today}｜{ticker} {shares}株{action} 約定（${price}・£{cash_delta_gbp:+.2f}）"
    )

    save_holdings(holdings_data)
    print(f"✅ holdings.json 更新: {ticker} {action} {shares}株 @${price}")
    return holdings_data


# ====== メイン ======
def cmd_sync():
    holdings_data = load_holdings()
    tickers = list(holdings_data["holdings"].keys())
    print(f"=== 価格取得中 (Twelve Data): {tickers} ===")
    gbp_usd = fetch_gbp_usd()
    prices = fetch_prices(tickers)
    print(f"GBP/USD: {gbp_usd}")
    for t, p in prices.items():
        print(f"  {t}: ${p}")
    update_memory_02(holdings_data, prices, gbp_usd)


def cmd_record_trade(args):
    holdings_data = record_trade(
        ticker=args.ticker,
        action=args.action,
        shares=args.shares,
        price=args.price,
        cash_delta_gbp=args.cash_delta_gbp,
        note=args.note or "",
    )

    # 02再生成
    tickers = list(holdings_data["holdings"].keys())
    gbp_usd = fetch_gbp_usd()
    prices = fetch_prices(tickers)
    update_memory_02(holdings_data, prices, gbp_usd)

    # Notionテーブル追記
    if NOTION_TOKEN:
        today = datetime.now().strftime("%Y-%m-%d")
        action_jp = {"BUY": "買い", "SELL": "売り"}.get(args.action, args.action)
        append_notion_trade_row(
            date_str=today,
            ticker=args.ticker,
            action_jp=action_jp,
            price_usd=args.price,
            shares=args.shares,
            realized_pnl_gbp=args.realized_pnl_gbp,
            note=args.note or "",
        )
    else:
        print("⚠️ NOTION_TOKEN 未設定のためNotion更新スキップ")


def main():
    parser = argparse.ArgumentParser(description="Portfolio state sync (single source: holdings.json)")
    parser.add_argument("--record-trade", action="store_true", help="売買を記録する")
    parser.add_argument("--ticker", help="銘柄ティッカー")
    parser.add_argument("--action", choices=["BUY", "SELL"], help="売買種別")
    parser.add_argument("--shares", type=float, help="株数")
    parser.add_argument("--price", type=float, help="約定価格 (USD)")
    parser.add_argument("--cash-delta-gbp", type=float, default=0.0,
                        help="現金変動 (GBP・売却なら+, 購入なら-)")
    parser.add_argument("--realized-pnl-gbp", type=float, default=None,
                        help="実現損益 (GBP・任意)")
    parser.add_argument("--note", default="", help="メモ")
    args = parser.parse_args()

    if args.record_trade:
        required = ["ticker", "action", "shares", "price"]
        missing = [k for k in required if getattr(args, k) is None]
        if missing:
            parser.error(f"--record-trade には {missing} が必須です")
        cmd_record_trade(args)
    else:
        cmd_sync()


if __name__ == "__main__":
    main()
