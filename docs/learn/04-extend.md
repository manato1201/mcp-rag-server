# 4. 拡張のしかた(レシピ)

どのレシピも、**テストを先に(または同時に)**書きます。検索を変えるときは、**測る**(評価セット)。

## レシピ A: 新しい文書形式を足す

1. 変換は `markitdown` が担当。対応する拡張子なら、`document_processor.py` の対象の拡張子の一覧(`cli.py` の数え上げ・`process_directory`)に足すだけ。
2. 対応していない形式は、`read_file` / `convert_to_markdown` に、**その形式専用の読み込み**を足す(最後に、必ずテキストを返す)。
3. テスト: 小さなサンプルを `tmp_path` に作り、`process_file` の結果(チャンクの数・本文)を確かめる。

## レシピ B: 新しい MCP の道具を足す

1. `rag_tools.py` に、ハンドラ関数 `xxx_handler(params, rag_service)` を書く。**例外でなく、`{"content": [...], "isError": true}` で失敗を返す**(AI が文面を読める)。
2. `register_rag_tools` の中で、`server.register_tool(name, description, input_schema, handler)`。`input_schema` は JSON Schema(`required` を正しく)。
3. 別モジュールで足すなら、`register_tools(server)` を持つモジュールを作り、`--module myapp.tools` で読み込む(`main.py` が対応済み)。
4. テスト: `MCPServer` に登録して、`_handle_request` に `tools/call` を渡す([講義 第 5 回](../lecture/05-mcp-jsonrpc.md) の書き方)。
5. **標準出力に `print` を書かない**(プロトコルが壊れる)。

## レシピ C: チャンクの分け方を変える

- サイズ・オーバーラップは、CLI の引数(`--chunk-size`・`--chunk-overlap`)で変えられる。変えたら、**索引を作り直す**(`clear` → `index`)。
- 区切り文字(英語の「.」など)を足すなら、`split_into_chunks` の `next_newline` / `next_period` の探し方を拡張する。**性質のテスト**を足す(空でない・先頭と末尾を含む・オーバーラップ)。
- 変えたら、**検索の質が変わる**ので、評価セットで前後を比べる。

## レシピ D: 埋め込みモデルを変える

1. `.env`: `EMBEDDING_MODEL`・`EMBEDDING_DIM`・接頭辞(`EMBEDDING_PREFIX_QUERY` / `..._EMBEDDING`)を、モデルの説明に合わせる。
2. **索引をクリアして、作り直す**(次元・意味の空間が違う)。
3. 接頭辞が要るかは、モデルのカードで確かめる(要るのに付けないと、静かに精度が落ちる)。

## レシピ E: ランキングを変える(RRF の重み・件数)

[講義 第 7 回](../lecture/07-testing-capstone.md) の `weighted_rrf`。

1. `_rrf_merge` に引数(重み)を足す。**既定は今と同じ**(後方互換)。
2. `search` に渡し、`rag_service` → 道具の引数まで通すかを決める。
3. 性質のテスト(重みを変えると順位がどう動くか)。
4. **評価セット**(質問 20〜30 + 正解のファイル)で、Recall@5 を前後で比べる。

## レシピ F: namespace の決め方を変える

`VectorDatabase._namespace_from_path` だけを変える(最初の階層 → 別の規則)。**変えると、既存の索引と、コレクション名が合わなくなる**ので、作り直す。除外の規則(`_`・`.`)は、ここに集まっている。

## 完了のチェックリスト

- [ ] テストを足した(性質を書く。重いモデルを使わない)
- [ ] `pytest` が通る(古い 2 件の失敗は、既知。直したら、06 の表から消す)
- [ ] 検索を変えたなら、**評価セットで測った**
- [ ] 標準出力に `print` を書いていない
- [ ] `.env`・個人のパス・文書の内容を、git に入れていない
- [ ] 文書(README・講義・学習資料)が、実際の動作と合っている(`tests/test_docs.py` が通る)

次は [5. テストの書き方](05-testing.md)。
