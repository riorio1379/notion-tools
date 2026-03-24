"""
company_report.py
企業名を入力すると企業分析レポートを自動生成し、Notionの就活管理DBに保存する
Claude APIを使用（要: ANTHROPIC_API_KEY）
"""

import json
import os
import urllib.request
import anthropic
from datetime import datetime

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
JOB_DB_ID = "327972dc-26e6-8199-9cf7-c43f829027f4"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

PROFILE_SUMMARY = """
内垣 理央（28卒）
志望：商社・コンサル・デベロッパー・メガバンク・メーカー
強み：ロンドンWHV・バーテンダー経験・作務衣海外販売・TOKIUM長期インターン（新規事業開発）・ピータールーガーサーバー
軸：大手難関企業でビジネス基礎を学び、将来の起業の糧とする
"""


def generate_report(company):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None, "【エラー】ANTHROPIC_API_KEY が設定されていません。"

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""以下の就活生のプロフィールを踏まえ、「{company}」の企業分析レポートを日本語で作成してください。

{PROFILE_SUMMARY}

以下の8セクション構成でまとめてください：

1. 企業概要（設立・売上・従業員・事業内容）
2. 事業の強み・競合優位性
3. 就活生が注目すべき事業・部門
4. 求める人物像（企業が重視する資質）
5. このプロフィールとの相性分析（強みをどう活かせるか）
6. 想定される選考設問と回答の切り口
7. 業界での立ち位置・競合比較
8. 注意点・懸念点（NG条件・転勤等）

各セクションは具体的かつ簡潔に。面接官の視点から実用的な内容にしてください。
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text, None


def save_to_notion(company, report_text):
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"【企業分析】{company}"

    # レポートをセクションごとに分割してブロック化
    blocks = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [{"text": {"content": f"生成日: {today} | Claude API自動生成"}}],
            "icon": {"type": "emoji", "emoji": "🤖"},
            "color": "blue_background"
        }},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"text": {"content": report_text}}]
        }},
    ]

    payload = {
        "parent": {"database_id": JOB_DB_ID},
        "icon": {"type": "emoji", "emoji": "🏢"},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
        },
        "children": blocks
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data, headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    return result["url"]


def run(company=None):
    if not company:
        company = input("企業名: ").strip()

    print(f"\n{company} の企業分析レポートを生成中...")
    report, error = generate_report(company)

    if error:
        print(error)
        return

    print("\n=== レポート ===")
    print(report[:500] + "..." if len(report) > 500 else report)

    url = save_to_notion(company, report)
    print(f"\nNotion保存完了: {url}")
    return report


if __name__ == "__main__":
    run()
