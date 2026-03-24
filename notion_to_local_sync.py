"""
notion_to_local_sync.py
Notionの今日のTODOページのチェック状態をTODO.mdに反映する逆同期スクリプト
cronで5分ごとに実行される想定
"""

import json
import os
import re
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


def find_today_notion_page():
    """今日の日付のTODOページをNotionから検索"""
    today = datetime.now()
    title_keyword = today.strftime("%Y年%m月%d日")

    data = json.dumps({
        "query": title_keyword,
        "filter": {"value": "page", "property": "object"}
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.notion.com/v1/search",
        data=data, headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        results = json.loads(r.read())

    for page in results.get("results", []):
        props = page.get("properties", {})
        title_prop = props.get("title", {}).get("title", [])
        if title_prop:
            title = title_prop[0].get("plain_text", "")
            if title_keyword in title:
                return page["id"]
    return None


def get_notion_checked_items(page_id):
    """NotionページのチェックされたTo-Doブロックのテキストを取得"""
    req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    checked_texts = []
    for block in result.get("results", []):
        if block["type"] == "to_do" and block["to_do"]["checked"]:
            texts = block["to_do"]["rich_text"]
            if texts:
                checked_texts.append(texts[0]["plain_text"])
    return checked_texts


def update_todo_md(checked_texts):
    """TODO.mdの該当チェックボックスをチェック済みに更新"""
    if not checked_texts:
        return 0

    with open(TODO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    updated_count = 0
    for text in checked_texts:
        # テキストの最初の20文字で部分一致検索
        search_text = text[:30].strip()
        # [ ] の行を探して [x] に変換
        pattern = rf"(- \[ \] )({re.escape(search_text)})"
        if re.search(pattern, content):
            content = re.sub(pattern, rf"- [x] \2", content)
            updated_count += 1

    if updated_count > 0:
        with open(TODO_PATH, "w", encoding="utf-8") as f:
            f.write(content)

    return updated_count


def run():
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{today_str}] Notion → TODO.md 同期開始")

    page_id = find_today_notion_page()
    if not page_id:
        print("今日のNotionページが見つかりませんでした")
        return

    checked_texts = get_notion_checked_items(page_id)
    if not checked_texts:
        print("チェック済みアイテムなし")
        return

    print(f"Notionでチェック済み: {checked_texts}")
    count = update_todo_md(checked_texts)
    print(f"TODO.md更新: {count}件")


if __name__ == "__main__":
    run()
