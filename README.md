# MCP RAG Server

MCP RAG Serverは、Model Context Protocol (MCP)に準拠したRAG（Retrieval-Augmented Generation）機能を持つPythonサーバーです。マークダウン、テキスト、パワーポイント、PDFなど複数の形式のドキュメントをデータソースとして、multilingual-e5-largeモデルを使用してインデックス化し、ベクトル検索によって関連情報を取得する機能を提供します。

> **このフォークについて:** [karaage0703/mcp-rag-server](https://github.com/karaage0703/mcp-rag-server) をベースに、**ChromaDB バックエンド**（PostgreSQL/pgvector不要）・**Windows 11 ネイティブ動作**（Docker・WSL2不要）向けの改変を加えたバージョンです。

## 概要

このプロジェクトは、MCPサーバーの基本的な実装に加えて、RAG機能を提供します。複数形式のドキュメントをインデックス化し、自然言語クエリに基づいて関連情報を検索することができます。

**Obsidian vault との連携を想定した設計になっており、トップレベルフォルダ名が ChromaDB のコレクション名（namespace）になります。**

## 機能

- **MCPサーバーの基本実装**
  - JSON-RPC over stdioベースで動作
  - ツールの登録と実行のためのメカニズム
  - エラーハンドリングとロギング

- **RAG機能**
  - 複数形式のドキュメント（マークダウン、テキスト、パワーポイント、PDF）の読み込みと解析
  - 階層構造を持つソースディレクトリに対応
  - markitdownライブラリを使用したパワーポイントやPDFからのマークダウン変換
  - 選択可能なエンベディングモデル（multilingual-e5-large、ruriなど）を使用したエンベディング生成
  - **ChromaDB を使用したベクトルデータベース**（Docker不要、ローカルファイルとして永続化）
  - ベクトル検索による関連情報の取得
  - 前後のチャンク取得機能（コンテキストの連続性を確保）
  - ドキュメント全文取得機能（完全なコンテキストを提供）
  - 差分インデックス化機能（新規・変更ファイルのみを処理）
  - **Obsidian vault ネームスペース対応**（`_` または `.` プレフィックスのフォルダは自動除外）
  - **watchdog による自動インデックス化**（ファイル保存を監視して即時更新）

- **ツール**
  - ベクトル検索ツール（MCP）
  - ドキュメント数取得ツール（MCP）
  - インデックス管理ツール（CLI）

## 前提条件

| 項目 | 要件 |
|------|------|
| OS | Windows 11（macOS/Linux でも動作） |
| Docker | **不要** |
| WSL2 | **不要** |
| Python | uv が自動管理（**3.12 を使用**） |
| Claude Desktop | インストール済み |

## インストール

### 依存関係のインストール

```powershell
# uvがインストールされていない場合は先にインストール
winget install --id=astral-sh.uv -e

# Python 3.12 で仮想環境を作成（sentencepieceのwheel問題を回避）
uv sync --python 3.12
uv add chromadb watchdog pyyaml
```

> **注意:** `uv sync` のみだと Python 3.13 が選択され sentencepiece のビルドが失敗する場合がある。必ず `--python 3.12` を付けること。

### vector_database.py の差し替え（ChromaDB 対応版）

このフォークの `src/vector_database.py` は ChromaDB バックエンド実装済みのため、差し替え不要です。

オリジナルリポジトリから clone した場合は、このフォークの `src/vector_database.py` をコピーしてください。

### rag_tools.py の編集

`src/rag_tools.py` の `create_rag_service_from_env` 関数内を以下に変更します：

**変更前（PostgreSQL）:**
```python
vector_database = VectorDatabase(
    {
        "host":     os.environ.get("POSTGRES_HOST",     "localhost"),
        "port":     os.environ.get("POSTGRES_PORT",     "5432"),
        "user":     os.environ.get("POSTGRES_USER",     "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "password"),
        "database": os.environ.get("POSTGRES_DB",       "ragdb"),
    }
)
```

**変更後（ChromaDB）:**
```python
vector_database = VectorDatabase(
    {
        "chroma_path":   os.environ.get("CHROMA_PATH",   "./data/chroma"),
        "embedding_dim": os.environ.get("EMBEDDING_DIM", "1024"),
    }
)
```

### main.py への Windows UTF-8 対応パッチ

`src/main.py` の先頭付近、`import sys` の直後（`from dotenv` より前）に以下を追加します：

```python
import io

# Force UTF-8 for stdin/stdout on Windows (default is CP932, which corrupts Japanese)
if hasattr(sys.stdin, 'buffer'):
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
```

> **なぜ必要か:** Windows のデフォルトエンコーディングは CP932。MCP は stdin/stdout で JSON を読み書きするため、日本語クエリが文字化けして `TextEncodeInput must be Union[TextInputSequence, ...]` エラーになる。このフォークでは適用済み。

### 環境変数の設定

`.env` ファイルを作成し、以下の環境変数を設定します：

```env
# ChromaDB パス（ベクトルデータの保存先）
CHROMA_PATH=./data/chroma

# ドキュメントディレクトリ
SOURCE_DIR=C:\Users\YOUR_USERNAME\Desktop\GameDevelopment\DevelopmentRAGEnvironment\localRAG
PROCESSED_DIR=C:\Users\YOUR_USERNAME\Desktop\GameDevelopment\DevelopmentRAGEnvironment\localRAG\_rag_dashboard\.processed

# エンベディングモデル設定
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIM=1024
EMBEDDING_PREFIX_QUERY=query:
EMBEDDING_PREFIX_EMBEDDING=passage:
```

## エンベディングモデルの設定

### サポートされているモデル

#### multilingual-e5-large（デフォルト・推奨）
```env
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIM=1024
EMBEDDING_PREFIX_QUERY=query:
EMBEDDING_PREFIX_EMBEDDING=passage:
```

#### cl-nagoya/ruri-v3-30m
```env
EMBEDDING_MODEL=cl-nagoya/ruri-v3-30m
EMBEDDING_DIM=256
EMBEDDING_PREFIX_QUERY=検索クエリ:
EMBEDDING_PREFIX_EMBEDDING=検索文書:
```

### プレフィックスについて

多くのエンベディングモデル（特にE5系）では、テキストの種類に応じてプレフィックスを付けることで性能が向上します：

- **検索クエリ用**: `EMBEDDING_PREFIX_QUERY` - ユーザーの検索クエリに自動で追加
- **文書用**: `EMBEDDING_PREFIX_EMBEDDING` - インデックス化される文書に自動で追加

### モデル変更時の注意

エンベディングモデルを変更した場合は、ベクトル次元が変わる可能性があるため、既存のインデックスをクリアして再作成してください：

```powershell
uv run python -m src.cli clear
uv run python -m src.cli index
```

## Obsidian vault との連携

`SOURCE_DIR` 配下のトップレベルフォルダ名が ChromaDB のコレクション名（namespace）になります。

```
localRAG/
├── chat_logs\        → namespace: chat_logs
├── tutorials\        → namespace: tutorials
├── personal_notes\   → namespace: personal_notes
├── _rag_dashboard\   → 除外（_ プレフィックス）
└── _templates\       → 除外（_ プレフィックス）
```

`_` または `.` で始まるフォルダは自動的にインデックス対象外になります。

## 使い方

### MCPサーバーの起動

```powershell
uv run python -m src.main
```

オプションを指定する場合：

```powershell
uv run python -m src.main --name "my-rag-server" --version "1.0.0" --description "My RAG Server"
```

### コマンドラインツール（CLI）

#### インデックスのクリア

```powershell
uv run python -m src.cli clear
```

#### ドキュメントのインデックス化

```powershell
# デフォルト設定でインデックス化
uv run python -m src.cli index

# 特定のディレクトリをインデックス化
uv run python -m src.cli index --directory ./path/to/documents

# チャンクサイズとオーバーラップを指定
uv run python -m src.cli index -d ./data/source -s 300 -o 50

# 差分インデックス化（新規・変更ファイルのみ）
uv run python -m src.cli index -i
```

#### インデックス内のドキュメント数の取得

```powershell
uv run python -m src.cli count
```

### watchdog による自動インデックス化

`auto_index.py` を使うと、ファイル変更を監視して自動的にインデックスを更新できます：

```powershell
# バックグラウンドで起動
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run python auto_index.py"
```

起動後はファイルを保存するたびに自動インデックス化されます。

> **注意:** ChromaDB の HNSW インデックスはメモリにキャッシュされるため、インデックス化後は **MCP サーバーを再起動** しないと検索結果に反映されません。

### MCPホストでの設定

Claude Desktop の `claude_desktop_config.json` に以下を追加します：

```json
{
  "mcpServers": {
    "mcp-rag-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\YOUR_USERNAME\\Desktop\\GameDevelopment\\mcp-rag-server",
        "python",
        "-m",
        "src.main"
      ]
    }
  }
}
```

## RAGツールの使用方法

### search

ベクトル検索を行います。Claude Desktop / Claude Code では自然言語で話しかけるだけで自動的に使用されます。

```json
{
  "jsonrpc": "2.0",
  "method": "search",
  "params": {
    "query": "Pythonのジェネレータとは何ですか？",
    "limit": 5,
    "with_context": true,
    "context_size": 1,
    "full_document": false
  },
  "id": 1
}
```

#### パラメータの説明

- `query`: 検索クエリ（必須）
- `limit`: 返す結果の数（デフォルト: 5）
- `with_context`: 前後のチャンクも取得するかどうか（デフォルト: true）
- `context_size`: 前後に取得するチャンク数（デフォルト: 1）
- `full_document`: ドキュメント全体を取得するかどうか（デフォルト: false）

### get_document_count

インデックス内のドキュメント数を取得します。

```json
{
  "jsonrpc": "2.0",
  "method": "get_document_count",
  "params": {},
  "id": 2
}
```

## 使用例

1. ドキュメントファイルを `SOURCE_DIR` に配置します。サポートされるファイル形式：
   - マークダウン（.md, .markdown）
   - テキスト（.txt）
   - パワーポイント（.ppt, .pptx）
   - Word（.doc, .docx）
   - PDF（.pdf）

2. CLIコマンドでインデックス化します：
   ```powershell
   uv run python -m src.cli index
   ```

3. MCPサーバーを起動します：
   ```powershell
   uv run python -m src.main
   ```

4. Claude Desktop で自然言語で検索します：
   ```
   mcp-rag-server で「Houdini VEX」について検索して
   ```

## バックアップと復元

ChromaDB はローカルファイルとして保存されるため、バックアップは簡単です。

### バックアップ

```powershell
# ZIP 圧縮
Compress-Archive -Path ".\data\chroma" -DestinationPath ".\chroma_backup.zip"
```

### 復元

```powershell
Expand-Archive -Path ".\chroma_backup.zip" -DestinationPath ".\data\"
```

## ディレクトリ構造

```
mcp-rag-server/
├── data/
│   ├── chroma/        # ChromaDB データ（自動生成）
│   └── processed/     # 処理済みファイル（テキスト抽出済み）
│       └── file_registry.json  # 差分インデックス用
├── src/
│   ├── __init__.py
│   ├── document_processor.py  # ドキュメント処理
│   ├── embedding_generator.py # エンベディング生成
│   ├── main.py                # エントリーポイント（UTF-8パッチ適用済み）
│   ├── mcp_server.py          # MCPサーバー
│   ├── rag_service.py         # RAGサービス
│   ├── rag_tools.py           # RAGツール
│   └── vector_database.py     # ChromaDB バックエンド
├── auto_index.py      # watchdog 自動インデックス化スクリプト
├── .env               # 環境変数設定ファイル
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## トラブルシューティング

### sentencepiece のビルドが失敗する

Python 3.13 では wheel がないためビルドが失敗する。

```powershell
uv sync --python 3.12
```

### `KeyError: 'chunk_index'` が出る

旧バージョンの `vector_database.py` を使用している。このフォークでは修正済み。`search()` 内の `results.append(...)` に以下が含まれているか確認：

```python
"chunk_index": meta.get("chunk_index", 0),
```

### `KeyError: 'document_id'` が出る

`get_adjacent_chunks()` / `get_document_by_file_path()` が `document_id` を返していない旧バージョン。このフォークでは `res["ids"]` を zip して `document_id` を含める実装になっている。

### 日本語クエリが文字化け / `TextEncodeInput` エラー

`src/main.py` に UTF-8 パッチが適用されているか確認。このフォークでは適用済み。

```
# エラーメッセージ例
TextEncodeInput must be Union[TextInputSequence, ...]
received query: '繝輔か繝ｼ繝...'  ← 文字化けしている
```

### インデックス化後も MCP の検索結果が増えない

ChromaDB の HNSW インデックスはメモリにロードされるため、別プロセスが upsert しても MCP サーバー側に反映されない。**インデックス化後は必ず MCP サーバーを再起動する。**

- Claude Desktop: タスクトレイから完全終了 → 再起動
- Claude Code: 接続を一度切断してから再接続

### `'NoneType' object has no attribute 'get_or_create_collection'`

`vector_database.py` の `initialize_database()` が `self.connect()` を呼んでいない旧バージョン。このフォークでは修正済み。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。
