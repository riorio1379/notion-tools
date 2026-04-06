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
DAILY_PATH = os.path.expanduser("~/DAILY.md")


def parse_today_todo():
    """DAILY.mdから今日のセクションを抽出"""
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    with open(DAILY_PATH, "r", encoding="utf-8") as f:
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


def get_child_pages():
    """HOME_PAGE_IDの子ページ一覧を取得"""
    pages = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{HOME_PAGE_ID}/children"
        if cursor:
            url += f"?start_cursor={cursor}"
        req = urllib.request.Request(url, headers=HEADERS, method="GET")
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        for block in result.get("results", []):
            if block.get("type") == "child_page":
                pages.append(block)
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")
    return pages


def archive_page(page_id):
    """Notionページをアーカイブ（削除）"""
    payload = json.dumps({"archived": True}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=payload, headers=HEADERS, method="PATCH"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def cleanup_old_todo_pages(keep_days=2):
    """直近keep_days日分以外のTODOページを削除"""
    from datetime import timedelta
    today = datetime.now().date()
    cutoff = today - timedelta(days=keep_days - 1)  # keep_days日前より古いものを削除

    pages = get_child_pages()
    deleted = []
    for page in pages:
        title = page.get("child_page", {}).get("title", "")
        # "📅 2026年04月01日 TODO" 形式を解析
        m = re.search(r"(\d{4})年(\d{2})月(\d{2})日", title)
        if not m:
            continue
        page_date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        try:
            page_date = datetime.strptime(page_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if page_date < cutoff:
            archive_page(page["id"])
            deleted.append(page_date_str)

    if deleted:
        print(f"古いTODOページを削除: {', '.join(deleted)}")


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
    cleanup_old_todo_pages(keep_days=2)
    open_notion(url)
    return url


if __name__ == "__main__":
    run()
