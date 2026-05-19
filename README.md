# automation

Personal automation scripts for Notion・portfolio management・daily routines.

GitHub repo name は歴史的経緯で `notion-tools` のままです（ローカルのフォルダ名は `automation/` に統一済み）。

## Scripts

| スクリプト | 役割 |
|-----------|------|
| `stock_price.py` | 保有銘柄の株価を Twelve Data API から取得し、Notion 株価履歴DBに日次1行記録 |
| `sync_portfolio_state.py` | `holdings.json` を Single Source of Truth として、`02_現状.md` と Notion 売買記録テーブルを同期 |
| `trade_journal.py` | 株式売買時に8セクション構造の詳細ページを銘柄分析DBに作成 |
| `holdings.json` | ポートフォリオ状態のマスターファイル（手動編集禁止・スクリプト経由のみ） |
| `price_alert.py` | 株価アラート（条件設定でPush通知） |
| `company_report.py` | 企業調査レポート自動生成 |
| `es_draft.py` | ES下書き生成補助 |
| `job_deadline_collector.py` | 就活締切情報の自動収集 |

## Setup

### 環境変数

```bash
# ~/.zshrc などに記載
export NOTION_TOKEN="ntn_..."
export TWELVE_DATA_API_KEY="..."
```

### 依存

- Python 3.x（macOS標準のものでOK）
- 標準ライブラリのみ使用（外部依存なし）

## Usage

### 日次株価記録（朝のルーティンで自動実行）

```bash
python3 ~/automation/stock_price.py
```

保有銘柄は `holdings.json` から読み込まれます。

### 売買約定時の同期（4箇所を1コマンドで）

```bash
python3 ~/automation/sync_portfolio_state.py --record-trade \
  --ticker NVDA --action SELL --shares 10 --price 235.42 \
  --cash-delta-gbp +1736.19 --note "決算前PARTIAL SELL"
```

これで以下が**同時に**更新されます：
- `holdings.json`（株数・現金残高）
- `~/RIO/Memory/02_現状_就活と投資の最新状況.md`（ポートフォリオ表）
- Notion 📋売買記録ページ（売買履歴テーブル）

### 株価のみ最新化（売買なし）

```bash
python3 ~/automation/sync_portfolio_state.py
```

## 設計思想

- **Single Source of Truth**：`holdings.json` をマスターとして、他は機械的に同期
- **手動同期の排除**：同じ情報を複数箇所で管理しない
- **設定の外部化**：API キーやトークンは環境変数経由
- **冪等性**：何度実行しても同じ結果になる

## 関連ドキュメント

- グローバル設定: `~/.claude/CLAUDE.md`（旧 `~/CLAUDE.md` から 2026-05-19 に移動）
- メモリファイル: `~/RIO/Memory/`
- 売買ルール: `~/RIO/Memory/feedback_売買記録の自動化.md`
