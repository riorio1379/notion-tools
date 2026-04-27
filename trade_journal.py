"""
trade_journal.py
株式売買記録をNotionの銘柄分析DBに自動作成するスクリプト
DB ID: 329972dc-26e6-8110-ad76-c986f89b4421
"""

import json
import os
import urllib.request
from datetime import datetime

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DB_ID = "329972dc-26e6-8110-ad76-c986f89b4421"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def create_trade_record(
    ticker: str,
    order_type: str,        # 例: "指値売り", "逆指値損切り", "成行買い"
    price: float,
    quantity: float,
    account: str,           # 例: "Freetrade ISA"
    portfolio_notes: str,   # ポートフォリオ状況メモ
    market_notes: str,      # 市場・株価状況メモ
    technical_notes: str,   # テクニカル分析メモ
    fundamental_notes: str, # ファンダメンタル分析メモ
    thought_process: str,   # 思考プロセス・判断理由
    sector: str = "",
):
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"{ticker} {order_type} ${price} ({today})"

    content_blocks = [
        _heading("① 注文概要"),
        _paragraph(f"銘柄: {ticker}\n注文タイプ: {order_type}\n価格: ${price}\n株数: {quantity}\n口座: {account}"),
        _heading("② 注文時のポートフォリオ状況"),
        _paragraph(portfolio_notes),
        _heading("③ 市場・株価状況"),
        _paragraph(market_notes),
        _heading("④ テクニカル分析"),
        _paragraph(technical_notes),
        _heading("⑤ ファンダメンタル分析"),
        _paragraph(fundamental_notes),
        _heading("⑥ 思考プロセス・判断理由"),
        _paragraph(thought_process),
        _heading("⑦ 売買結果"),
        _paragraph("（約定後に記入）"),
        _heading("⑧ 今回の取引で学んだこと"),
        _paragraph("（後日記入）"),
    ]

    properties = {
        "銘柄名": {"title": [{"text": {"content": title}}]},
    }
    if ticker:
        properties["ティッカー"] = {"rich_text": [{"text": {"content": ticker}}]}
    if sector:
        properties["セクター"] = {"select": {"name": sector}}

    payload = {
        "parent": {"database_id": DB_ID},
        "properties": properties,
        "children": content_blocks,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data,
        headers=HEADERS,
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"作成完了: {result['url']}")
    return result


def _heading(text):
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text}}]}}


def _paragraph(text):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text}}]}}


if __name__ == "__main__":
    # 使用例
    create_trade_record(
        ticker="CRCL",
        order_type="指値売り",
        price=129.0,
        quantity=43.4,
        account="Freetrade ISA",
        portfolio_notes="トランシェA: 12.26株 @$109.97 / トランシェB: 31.14株 @$199.92\nBEP: £129.15（GBP建て）≈ $167（USD建て）\n含み損: 約£1,495",
        market_notes="現在値: ~$121 / RSI: 79〜85（過熱域）\nアナリスト目標: $11〜$26（IPO直後のため少数）",
        technical_notes="主要レジスタンス: $129.52\n主要サポート: $119.33\n→ $129でレジスタンス手前の指値売り",
        fundamental_notes="P/S比: 11.3倍（業界平均3.4倍の3.3倍）\nMiCA対応唯一のステーブルコイン（EU規制2026年7月完全施行）",
        thought_process="1. RSI過熱域で短期調整リスク高い\n2. BEPまで遠く長期保有は含み損継続の可能性\n3. ISA口座のため損失確定にデメリットなし\n4. $129でレジスタンス手前売り + $118で損切り設定",
        sector="フィンテック・ステーブルコイン",
    )
