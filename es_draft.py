"""
es_draft.py
企業・設問情報を入力するとES下書きを生成し、Notionの就活管理DBに保存する
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

# ユーザープロフィール（CLAUDE.mdから抜粋）
PROFILE = """
【内垣 理央 プロフィール】
- 早稲田大学文化構想学部・国家ダイナミクスプログラム（2027年9月卒業予定・28卒）
- 2024年9月〜2025年末：ロンドンWHV。ロンドン最古のクラシックバーでバーテンダーとして週50時間勤務。
  作務衣をロンドンのマーケットで30着以上販売し、日本文化を欧州に発信。
- 早稲田大学 繊維研究会（服飾団体）代表：30人以上を統率、ファッションショー来客200人達成
- ピータールーガーステーキハウス東京（2022年9〜2024年8月）：学生最速でメインサーバーに昇格。
  繁忙期シャンパン販売グランプリで毎回トップ3入り。スタッフトレーナーも担当。
- 株式会社TOKIUM 社長直下・新規事業開発部 長期インターン（約1年）：
  契約書管理システムの立ち上げ。架電→アポ→商談→契約まで全業務を一人で完遂。週10件の契約獲得を達成した時期あり。
- 志望業界：商社・コンサル・デベロッパー・メガバンク・メーカー（味の素・サントリー第一志望）
- 強み：上昇志向・海外経験・客観視・人見知りしない・努力家
- 語学：英語（日常会話〜ビジネスレベル）
"""


def count_chars(text):
    """文字数カウント（スペース・改行除く）"""
    return len(text.replace(" ", "").replace("\n", "").replace("　", ""))


def generate_draft(company, question, char_limit, extra_info=""):
    """Claude APIでES下書き生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "【エラー】ANTHROPIC_API_KEY が設定されていません。\nexport ANTHROPIC_API_KEY='your_key' を実行してください。"

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""あなたは就活ESの専門家です。以下のプロフィールと設問をもとに、{char_limit}字以内のES下書きを作成してください。

{PROFILE}

【企業名】{company}
【設問】{question}
【文字数制限】{char_limit}字以内
【補足情報】{extra_info if extra_info else 'なし'}

要件：
- 具体的なエピソードと数字を盛り込む
- 結論→根拠→具体例→学び・再現性の構成
- {char_limit}字の90%以上を使い切ること
- 自然な日本語で、面接官の印象に残る文章
- 最後に文字数を【XX字】と明記すること
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def save_to_notion(company, question, char_limit, draft):
    """Notionの就活管理DBに保存"""
    char_count = count_chars(draft)
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"{company} ES - {question[:20]}..."

    payload = {
        "parent": {"database_id": JOB_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
        },
        "children": [
            {"object": "block", "type": "heading_2", "heading_2": {
                "rich_text": [{"text": {"content": "📝 設問情報"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {
                "rich_text": [{"text": {"content": f"企業: {company}"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {
                "rich_text": [{"text": {"content": f"設問: {question}"}}]}},
            {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {
                "rich_text": [{"text": {"content": f"文字数制限: {char_limit}字以内"}}]}},
            {"object": "block", "type": "heading_2", "heading_2": {
                "rich_text": [{"text": {"content": f"✏️ 下書き（{char_count}字）"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"text": {"content": draft}}]}},
            {"object": "block", "type": "heading_2", "heading_2": {
                "rich_text": [{"text": {"content": "🔄 修正履歴"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"text": {"content": f"v1: {today} 初稿生成"}, "annotations": {"color": "gray"}}]}},
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


def run(company=None, question=None, char_limit=None, extra_info=""):
    if not company:
        company = input("企業名: ").strip()
    if not question:
        question = input("設問: ").strip()
    if not char_limit:
        char_limit = int(input("文字数制限: ").strip())

    print(f"\n{company} の ES を生成中...")
    draft = generate_draft(company, question, char_limit, extra_info)
    char_count = count_chars(draft)

    print("\n=== 下書き ===")
    print(draft)
    print(f"\n文字数: {char_count}字 / {char_limit}字")

    url = save_to_notion(company, question, char_limit, draft)
    print(f"\nNotion保存完了: {url}")
    return draft


if __name__ == "__main__":
    run()
