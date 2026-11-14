# MCP RAG Server

ローカルの文書(Markdown・テキスト・PDF・Word・PowerPoint)を索引にして、**AI アプリ(Claude Desktop など)が、質問のたびに関連する断片を検索できる**ようにする MCP サーバー。
すべてこの PC の中で動く(文書もベクトルも、外へ送らない)。

> **このフォークについて**: [karaage0703/mcp-rag-server](https://github.com/karaage0703/mcp-rag-server)(MIT)をもとに、**ChromaDB**(Docker・PostgreSQL 不要)・**Windows 11 ネイティブ**・**Obsidian vault**(最初の階層のフォルダ = namespace)・**日本語の語の検索(BM25 + SudachiPy)**に向けた改変を加えています。

![構成図](docs/diagrams/architecture.svg)

## 特徴

| | |
|---|---|
| **ハイブリッド検索** | 意味(ベクトル)+ 語(BM25)を、RRF(順位の融合)で合わせる。型番(`BTQ-116`)も、言い換えも拾う |
| **日本語** | SudachiPy で語に分け、助詞を除き、辞書形に直す。英数字の型番は別に拾う |
| **前後の文脈** | 見つけた断片の前後のチャンク・文書の全文も返せる |
| **差分インデックス** | 変わったファイルだけを処理(ハッシュ・更新日時・サイズ) |
| **Obsidian** | トップレベルのフォルダ = namespace(`_`・`.` で始まるものは除外)。`auto_index.py` が保存を監視して自動更新 |
| **MCP** | 標準入出力の JSON-RPC。道具は `search`・`get_document_count` |

## クイックスタート

```powershell
winget install --id=astral-sh.uv -e          # uv が無ければ
uv sync --python 3.12                        # 必ず 3.12(sentencepiece のビルドのため)
uv add chromadb watchdog pyyaml
```

`.env` を作る(**git に入れない**。詳しくは [設定](docs/learn/01-overview.md#14-設定env)):

```env
CHROMA_PATH=./data/chroma
SOURCE_DIR=<文書のあるフォルダ>
PROCESSED_DIR=<変換済みの置き場>
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIM=1024
EMBEDDING_PREFIX_QUERY=query:
EMBEDDING_PREFIX_EMBEDDING=passage:
```

索引を作る:

```powershell
uv run python -m src.cli index               # 全部
uv run python -m src.cli index -i            # 差分(新規・変更だけ)
uv run python -m src.cli count               # 件数
uv run python -m src.cli clear               # 索引を消す(モデルを変えたとき)
```

Claude Desktop の `claude_desktop_config.json` に登録する:

```json
{
  "mcpServers": {
    "mcp-rag-server": {
      "command": "uv",
      "args": ["run", "--directory", "<このリポジトリのパス>", "python", "-m", "src.main"]
    }
  }
}
```

## 道具

| 道具 | 引数 | 内容 |
|---|---|---|
| `search` | `query`(必須)・`limit`(5)・`with_context`(true)・`context_size`(1)・`full_document`(false) | 関連する断片を、ファイルごとにまとめて返す |
| `get_document_count` | なし | 索引の断片の数 |

## 自動インデックス(Obsidian)

`auto_index.py` が vault を監視し、Markdown が保存されたら、差分の索引を実行します(3 秒のデバウンス)。
**冒頭の設定(`VAULT`・`MCP_RAG_DIR`)が、特定の PC のパスに固定**されています。使う前に、自分の環境に書き換えてください(詳しくは [既知の問題](docs/learn/06-troubleshooting-maintenance.md#62-既知の問題コードと文書の食い違い))。

## 状態と既知の問題

- テスト: `uv run pytest -q`(検索の核 14 件・MCP・接頭辞が通る。**古い 2 件が失敗**。PostgreSQL 時代のテスト)。
- **検索の精度を測る仕組みは、まだありません**。
- 主な既知の問題: 前後の文脈の断片に印が付かない(表示が「検索ヒット」になる)・削除/短縮したファイルの古いチャンクが残る・`status: archived` が CLI の索引で効かない・`CLAUDE.md` が PostgreSQL 版のまま。**一覧と直し方の案**は [トラブルシュートとメンテナンス](docs/learn/06-troubleshooting-maintenance.md)。

## ドキュメント

| 読むもの | 内容 |
|---|---|
| [**講義資料**](docs/lecture/index.md) | **基礎から**(RAG・チャンク・埋め込み・BM25・RRF・MCP・運用・テスト)。全 8 回・実行できる例と確認問題つき |
| [**学習資料**](docs/learn/index.md) | **保守・拡張の実務編**(全体像・コードの読み方・レシピ・テスト・トラブルシュート・用語集) |
| [導入・設定の詳しい手順](docs/reference/setup-notes.md) | 元の README(Obsidian 連携・バックアップ・トラブルシューティングなど) |

## ライセンス

MIT(元のリポジトリと同じ)。[LICENSE](LICENSE)
