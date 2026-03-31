"""
daily_todo_sync.py
TODO.md の今日のセクションをNotionに同期し、Notionアプリを起動する
"""

import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
HOME_PAGE_ID = "327972dc-26e6-8010-bd24-cd5d20bbb4c1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
TODO_PATH = os.path.expanduser("~/TODO.md")


def parse_today_todo():
    """TODO.mdから今日のセクションを抽出"""
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    with open(TODO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 今日の日付を含むセクションを探す
    pattern = rf"## {date_str}.*?(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None, date_str

    return match.group(0).strip(), date_str


def md_to_blocks(section_text):
    """MarkdownテキストをNotionブロックのリストへDB変換"""
    blocks = []
    lines = section_text.split("\n")

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        # h2: ## タイトル
        if line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": line[3:]}}]}})

        # h3: ### セクション
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"text": {"content": line[4:]}}]}})

        # チェックボックス: - [x] or - [ ]
        elif re.match(r"- \[[ x]\]", line):
            checked = line[3] == "x"
            text = line[6:].strip()
            blocks.append({"object": "block", "type": "to_do",
                "to_do": {
                    "rich_text": [{"text": {"content": text}}],
                    "checked": checked
                }})

        # 通常リスト: -
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": line[2:]}}]}})

        # 通常テキスト
        elif not line.startswith("#"):
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": line}}]}})

    return blocks


def create_notion_page(date_str, blocks):
    """Notionにその日のTODOページを作成"""
    today = datetime.now()
    title = f"📅 {today.strftime('%Y年%m月%d日')} TODO"

    payload = {
        "parent": {"page_id": HOME_PAGE_ID},
        "icon": {"type": "emoji", "emoji": "📅"},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
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


def open_notion(url=None):
    """Notionアプリを起動"""
    try:
        if url:
            notion_url = url.replace("https://www.notion.so/", "notion://www.notion.so/")
            subprocess.Popen(["open", "-a", "Notion", notion_url])
        else:
            subprocess.Popen(["open", "-a", "Notion"])
        print("Notionアプリを起動しました")
    except Exception as e:
        print(f"Notion起動失敗: {e}")


def run():
    print("=== TODO → Notion 同期中 ===")
    section, date_str = parse_today_todo()

    if not section:
        print(f"今日（{date_str}）のTODOセクションが見つかりませんでした")
        open_notion()
        return

    blocks = md_to_blocks(section)
    url = create_notion_page(date_str, blocks)
    print(f"Notion同期完了: {url}")
    open_notion(url)
    return url


if __name__ == "__main__":
    run()
