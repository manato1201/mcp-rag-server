# 5. テストの書き方・動かし方

## 5.1 動かす

```bash
uv sync --extra dev                       # pytest を入れる
uv run pytest -q                          # 全部(約 30 秒。埋め込みモデルは読み込まない)
uv run pytest tests/test_search_core.py -q
uv run pytest -k rrf -q                   # 名前で絞る
```

**今の状態**: 古い 2 件(`test_vector_database.py`)が失敗する(PostgreSQL 時代の `EMBEDDING_DIM`・テーブル作成が前提)。直すか消すまで、**新しい失敗が、古い失敗に紛れる**ので、気をつける。

## 5.2 どこに足すか

| 変えたもの | 足す場所 |
|---|---|
| チャンク・RRF・トークン化・namespace | `tests/test_search_core.py` |
| MCP の道具・JSON-RPC | `tests/test_mcp_server.py` |
| 埋め込みの接頭辞 | `tests/test_embedding_generator.py` |
| 文書 | `tests/test_docs.py`(引用・実行例・リンク・図の検査。足すものは無い) |

## 5.3 重いものを避ける

| 重いもの | 避け方 |
|---|---|
| 埋め込みモデル(読み込みに数秒〜数十秒・ダウンロード) | `EmbeddingGenerator._add_prefix(None, ...)` のように**クラスから直接**。モデルが要る処理は、`patch` で偽物を渡す(`test_embedding_generator.py` が見本) |
| ChromaDB の接続 | `VectorDatabase({...})` は `connect()` まで開かない。静的メソッド(`_rrf_merge`)は、そのまま呼ぶ |
| Sudachi | `vd._use_sudachi = False` で、代替(正規表現)の経路を再現できる |
| 標準出力 | `contextlib.redirect_stdout(io.StringIO())` で捕まえる([講義 第 5 回](../lecture/05-mcp-jsonrpc.md)) |
| 環境変数 | `monkeypatch.setenv`(テストの後で、自動で元に戻る) |

## 5.4 性質を書く

例を 1 つ書くより、**どんな入力でも成り立つ性質**を書く方が、実装が変わっても壊れにくい。

- チャンク: 空でない・先頭が元の先頭・末尾が元の末尾・隣と重なる・**必ず終わる**(大きなオーバーラップでも)。
- RRF: 両方に出たものが 1 位・片方にしか出なくても残る・件数を超えない・式どおりの点。
- トークン化: 重複が無い・型番が丸ごと入る・Sudachi が無くても動く。

## 5.5 文書のテスト

```bash
uv run pytest tests/test_docs.py -q
python tools/quote_code.py docs --outputs    # 引用の更新・実行例の出力の作り直し
python tools/check_mermaid.py                # 図が描画できるか(mmdc が要る)
```

- 実行例は、リポジトリのルートで、`-I` なしで動かす(`src` を import できるように)。**2 回実行して、出力が一致するか**を確かめる。乱数・時刻・パスを出力しない。
- 実行例は、重いモデルを読み込まない(接続しない `VectorDatabase`・クラスから直接のメソッド)。

## 5.6 評価(検索の質)

**テストは、動くことを確かめるもので、検索が良いことは保証しない**。質を測るには、評価セットが要る([講義 第 7 回](../lecture/07-testing-capstone.md))。

1. 自分の vault から、質問 20〜30 個と、正解のファイルを決める(型番を含む質問・含まない質問の両方)。
2. 上位 5 件に正解が入る割合(Recall@5)を、変更の前後で比べる。
3. 結果は、**日付・件数・設定**とともに記録する。

次は [6. トラブルシュートとメンテナンス](06-troubleshooting-maintenance.md)。
