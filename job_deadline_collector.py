"""
job_deadline_collector.py
28卒就活の締切情報をClaude APIで収集し、Notionの就活管理DBに自動追加する
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

TARGET_COMPANIES = [
    "味の素", "サントリー", "アサヒビール", "キリンホールディングス",
    "三菱商事", "伊藤忠商事", "住友商事", "丸紅", "豊田通商",
    "マッキンゼー", "BCG", "ベイン", "デロイト", "アクセンチュア",
    "三菱UFJ銀行", "三井住友銀行", "みずほ銀行",
    "三菱地所", "三井不動産", "住友不動産",
    "リクルート", "サイバーエージェント",
]


def collect_deadlines():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("【エラー】ANTHROPIC_API_KEY が設定されていません。")
        return []

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now().strftime("%Y-%m-%d")
    companies_str = "、".join(TARGET_COMPANIES)

    prompt = f"""今日は{today}です。
28卒（2027年9月卒業）の就活において、以下の企業・業界の直近の締切情報を教えてください：
{companies_str}

各企業について以下の形式でリスト化してください：
- 企業名 | 選考種別（ES/説明会/インターン等）| 締切日 | 備考

知らない場合は「情報なし」と記載。
現在（{today}）から3ヶ月以内の締切に絞ってください。"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def save_to_notion(deadlines_text):
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"【締切情報】{today} 自動収集"

    payload = {
        "parent": {"database_id": JOB_DB_ID},
        "icon": {"type": "emoji", "emoji": "📅"},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
        },
        "children": [
            {"object": "block", "type": "callout", "callout": {
                "rich_text": [{"text": {"content": f"自動収集日: {today} ※必ず公式サイトで確認すること"}}],
                "icon": {"type": "emoji", "emoji": "⚠️"},
                "color": "yellow_background"
            }},
            {"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"text": {"content": deadlines_text}}]
            }},
        ]
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
    print("=== 28卒 就活締切情報を収集中 ===")
    deadlines = collect_deadlines()
    if not deadlines:
        return

    print(deadlines[:300] + "...")
    url = save_to_notion(deadlines)
    print(f"\nNotion保存完了: {url}")
    return deadlines


if __name__ == "__main__":
    run()
