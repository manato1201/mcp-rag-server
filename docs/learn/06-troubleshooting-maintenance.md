# 6. トラブルシュートとメンテナンス

## 6.1 症状から探す

| 症状 | 原因の候補 | 調べる・直す |
|---|---|---|
| 日本語のクエリが文字化け・`TextEncodeInput must be …` | stdin / stdout が CP932 | `src/main.py` の先頭の UTF-8 化が入っているか |
| ホストが接続できない・すぐ切れる | stdout に余計な出力(`print`)・起動の失敗 | ログ(`logs/mcp_rag_server.log`・stderr)。`print` を `logger` に |
| 「インデックスにドキュメントが存在しません」 | 索引を作っていない | `uv run python -m src.cli index`(`SOURCE_DIR` にファイルがあるか) |
| 検索しても出ない | namespace が違う・`_` `.` 始まりのフォルダ・索引が古い | `count`・フォルダ名・`index --incremental` |
| 型番で当たらない | BM25 が使えていない(`rank-bm25` が無い・索引が壊れた) | `data/chroma/bm25/` を消して、`index`(再構築) |
| モデルを変えたら、検索がおかしい | 次元・意味の空間が違う | `clear` → `index`(索引の作り直し) |
| 削除・移動したファイルが、検索に出る | 古いチャンクを消す処理が無い | `clear` → `index`(下の既知の問題) |
| ファイルを短くしたのに、古い内容が出る | 古い末尾のチャンクが残る | 同上 |
| `sentencepiece` のビルドが失敗 | Python のバージョン | Python 3.12 で仮想環境を作る(README の導入) |
| `KeyError: 'chunk_index'` / `'document_id'` | 古いスキーマで作った索引 | `clear` → `index`([元の README](../reference/setup-notes.md) のトラブルシューティング) |
| Sudachi が使われない | 未インストール・辞書が無い | `uv add sudachipy sudachidict-core`。無くても、代替で動く(粗い) |
| 索引の作成が遅い | 保存のたびに、BM25 を namespace 全体で再構築する | 一度に大量を入れる(`index`)。小さな変更は `--incremental` |

## 6.2 既知の問題(コードと文書の食い違い)

| # | 内容 | 影響 | 直し方の案 |
|---|---|---|---|
| 1 | **前後の文脈・全文の断片に、`is_context` / `is_full_document` が付かない**(`similarity` も無い) | 検索結果で、足した断片も「検索ヒット・類似度 0.00%」と表示される | `get_adjacent_chunks`・`get_document_by_file_path` が、印を付ける(`is_context: True`)。`rag_service` で足すときに付けてもよい |
| 2 | **古いチャンクを消す処理が呼ばれない**(`delete_by_file_path` は未使用) | ファイルを短く・削除しても、古い索引が残る | 再処理するファイルの旧チャンクを、入れる前に消す。削除は、`SOURCE_DIR` の一覧と突き合わせて検出 |
| 3 | **`status: archived` が、`src/` で効かない** | `auto_index.py` は再起動を避けるだけで、CLI の索引は、アーカイブ済みも対象 | `document_processor` が frontmatter を読み、`archived` を除外する |
| 4 | `auto_index.py` の冒頭の設定が、**特定の PC のパスに固定** | 他の PC・他のユーザーで動かすには、書き換えが要る | `.env` / 引数 / 相対パスにする。**パスにユーザー名が含まれるので、公開リポジトリに残すのは避ける** |
| 5 | `rag_tools.create_rag_service_from_env` に、**PostgreSQL 時代の環境変数**(`POSTGRES_*`)の読み取りが残る | 使われない設定が、混乱のもと | ChromaDB 版では不要な行を削除する |
| 6 | **`CLAUDE.md` が、PostgreSQL / pgvector 版の説明のまま** | AI や新しい参加者が、古い手順を信じる | ChromaDB 版(`CHROMA_PATH`・BM25・Sudachi)に書き直す |
| 7 | **`tests/test_vector_database.py` の 2 件が失敗**(PostgreSQL 時代の前提) | 新しい失敗が、古い失敗に紛れる | 現在の仕様に書き直すか、削除する |
| 8 | **検索の精度を測る仕組みが無い** | 変更の良し悪しを、数字で言えない | 評価セット + Recall@5([講義 第 7 回](../lecture/07-testing-capstone.md)) |
| 9 | BM25 の索引は **pickle** | 他人から受け取った `.pkl` を読むと、任意のコードが実行されうる | 自分で作ったものだけを読む。`bm25/` を共有しない |
| 10 | `expires` の処理は、**ノートを書き換える** | 意図しない変更 | vault をバックアップ。書き換えが不要なら、無効にする |

## 6.3 定期的にやること

| いつ | やること |
|---|---|
| 変更のたび | `pytest`・`tests/test_docs.py` |
| 月 1 回 | 依存の更新(`uv lock --upgrade`)→ テスト → 実際に検索して確認。`sentence-transformers`・`chromadb` は、大きく変わりうる |
| 埋め込みモデルを変えたとき | 索引の作り直し・評価セットでの比較 |
| vault を整理したとき | `clear` → `index`(古いチャンクを消す) |
| 公開の前 | `.env`・個人のパス・ノートの内容が、リポジトリに無いか(`.gitignore` の確認) |

## 6.4 公開の前の安全確認

```bash
git status --short
git diff --cached --stat
```

- `.env`・`logs/`・`data/`(文書・索引)・個人のパスを、追跡していないか。
- 文書の例に、**自分のノートの内容・実在のパス**が混ざっていないか(合成の例だけにする)。

次は [用語集](glossary.md)。
