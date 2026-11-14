# 学習資料(保守・拡張の実務編)

MCP RAG Server を **保守し、拡張できるようになる** ための資料。使うだけなら [README](../../README.md) で足ります。
基礎(RAG・埋め込み・BM25・RRF・MCP)から学ぶ人は、[講義資料](../lecture/index.md) を先に読むと楽です。

| 段階 | 読むもの | できるようになること |
|---|---|---|
| 0 | 動かす(下) | テストを走らせ、検索の部品を呼べる |
| 1 | [全体像](01-overview.md) | 索引と検索の流れを説明できる |
| 2 | [コードの読み方](02-code-tour.md)・[内側の仕組み](03-internals.md) | どのファイルに何があるか迷わない。検索の順序を追える |
| 3 | [拡張のしかた](04-extend.md)・[テスト](05-testing.md) | 新しい形式・道具・ランキングを、テストつきで足せる |
| 4 | [トラブルシュートとメンテナンス](06-troubleshooting-maintenance.md) | 症状から原因を探せる。既知の問題と直し方を知る |
| 補強 | [基礎の補強](07-foundations.md) | Python の基本・検索と AI の用語・設計思想・アルゴリズムを補える |
| (引く) | [用語集](glossary.md) | 分からない言葉が出たとき |

## まず動かす

```bash
uv sync --extra dev                          # 依存(pytest を含む)
uv run pytest -q                             # テスト(古い 2 件が失敗する。既知。06 を参照)
uv run python -m src.cli count               # 索引の件数
```

MCP ホスト(Claude Desktop)への登録は [README](../../README.md)。

## 関連

- [講義資料](../lecture/index.md) — 基礎から(全 8 回)
- [設定・導入の詳しい手順](../reference/setup-notes.md) — 元の README(参照用)
