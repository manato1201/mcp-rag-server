# MCP RAG Server のドキュメント

| あなたは | 読むもの |
|---|---|
| **使ってみたい** | [README](../README.md) |
| **導入・設定の詳細を見たい** | [元の README(参照)](reference/setup-notes.md) |
| **基礎から学びたい**(RAG・チャンク・埋め込み・BM25・RRF・MCP) | [講義資料](lecture/index.md)(全 8 回・実行できる例つき) |
| **保守・拡張したい** | [学習資料](learn/index.md)(全体像・コードの読み方・レシピ・テスト・トラブルシュート) |
| **分からない言葉がある** | [用語集](learn/glossary.md) |
| **設計の経緯を知りたい** | [design.md](design.md) |

## 図

| 図 | 内容 |
|---|---|
| [構成図](diagrams/architecture.svg) | MCP ホスト・サーバー・ローカルデータ・索引を作る側 |

フロー・シーケンスの図は、各ページの Mermaid です(GitHub でそのまま描かれます)。

## この文書を古くしない仕組み

- 講義の**コードの引用は、ソースから自動で作る**(`python tools/quote_code.py docs`)。
- `# 実行できる` の例は、テストが 2 回実行して、`# 出力` と一致するか確かめる。
- 検査: `uv run pytest tests/test_docs.py`。構成図は `python tools/make_diagrams.py`、Mermaid の描画は `python tools/check_mermaid.py`。
