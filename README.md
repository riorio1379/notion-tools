# notion-tools

Notion API scripts for personal productivity.

## Scripts

- `trade_journal.py` - 株式売買記録を銘柄分析DBに自動作成

## Setup

```bash
# Python 3が必要
python3 --version
```

### Claude Code セットアップ（新マシン移行時）

このリポジトリには `CLAUDE.md.template` が含まれています。
新しいマシンでClaude Codeを使う際は、以下のコマンドで `~/CLAUDE.md` を復元してください。

```bash
cp ~/notion-tools/CLAUDE.md.template ~/CLAUDE.md
```

> `~/CLAUDE.md` はClaude Codeがすべてのプロジェクトで読み込むグローバル設定ファイルです。
> このリポジトリの `CLAUDE.md.template` が最新の内容を管理しています。

## Usage

### trade_journal.py
株式の売買注文時に売買記録をNotionに作成するスクリプト。

```bash
python3 trade_journal.py
```
