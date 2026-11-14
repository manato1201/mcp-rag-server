# 第 7 回 テストと総合演習

> 所要時間の目安: 半日 / 前提: 第 1〜6 回

## この回のゴール

- このリポジトリのテストが**何を確かめ、何を確かめていないか**を説明できる。
- 重いモデル・データベースを使わずに、**検索の核を単体でテスト**する書き方が分かる。
- 検索の改良を 1 つ**自分で足し、効果を確かめられる**。

## 1. 今あるテスト

| ファイル | 確かめるもの |
|---|---|
| `tests/test_mcp_server.py` | MCP サーバー(道具の登録・`tools/call`・エラー・通知・リソース)。標準出力は**モック** |
| `tests/test_embedding_generator.py` | 接頭辞(`_add_prefix`・文書 / クエリ)。モデルは**偽物** |
| `tests/test_vector_database.py` | **古い**(PostgreSQL 時代の `EMBEDDING_DIM`・テーブル作成)。**2 件が失敗**する |
| `tests/test_search_core.py` | **検索の核**: チャンク分割・RRF・トークン化・namespace(重いモデル不要) |
| `tests/test_docs.py` | この文書(引用・実行例・リンク・図) |

**足りなかったもの**: チャンク分割・RRF・トークン化・namespace といった**検索の核**には、テストがありませんでした。
そこで `tests/test_search_core.py` を足しました(この回の内容)。

## 2. 重いものを避けてテストする

- **モデルを読み込まない**: `EmbeddingGenerator._add_prefix` は `self` を使わないので、`EmbeddingGenerator._add_prefix(None, text, prefix)` と、**クラスから直接**呼べる。
- **静的メソッドは、そのまま呼ぶ**: `VectorDatabase._rrf_merge(...)` は、データベースに接続しない。
- **接続しないオブジェクト**: `VectorDatabase({...})` は、`connect()` を呼ぶまで、ChromaDB を開かない。
- **一時フォルダ**: `tmp_path`(pytest)で、ファイルを作って壊さない。

```python
# 実行できる
from src.document_processor import DocumentProcessor
from src.vector_database import VectorDatabase

dp = DocumentProcessor()

# 性質を確かめる: どのチャンクも空でなく、つなぎ合わせると、元の文字をすべて含む
text = "第一の文です。第二の文です。第三の文です。\n第四の文です。" * 5
chunks = dp.split_into_chunks(text, chunk_size=30, overlap=5)
print("空のチャンクが無い:", all(chunks))
print("先頭は元の先頭から:", text.startswith(chunks[0]))
print("末尾は元の末尾まで:", text.endswith(chunks[-1]))

# 順位の性質: どちらにも出るものが、必ず 1 位になる
mk = lambda i: {"document_id": i, "content": i, "file_path": "", "chunk_index": 0, "similarity": 0.0}
top = VectorDatabase._rrf_merge([mk("x"), mk("both")], [mk("y"), mk("both")], limit=1)
print("RRF の 1 位:", top[0]["document_id"])
```

```text
# 出力
空のチャンクが無い: True
先頭は元の先頭から: True
末尾は元の末尾まで: True
RRF の 1 位: both
```

**例を 1 つ書くより、性質を書く**方が、実装が変わっても壊れにくい。

## 3. 総合演習: 重みつきの RRF

**課題**: 質問に**型番**が含まれるときは、BM25 の順位を重く見たい。RRF に**重み**を付けた `weighted_rrf` を作り、挙動を確かめます。

```text
重みつき RRF のスコア = w_vec / (k + ベクトルの順位) + w_bm25 / (k + BM25 の順位)
```

```python
# 実行できる
def weighted_rrf(vector_ids, bm25_ids, w_vec=1.0, w_bm25=1.0, k=60):
    scores = {}
    for rank, d in enumerate(vector_ids):
        scores[d] = scores.get(d, 0.0) + w_vec / (k + rank + 1)
    for rank, d in enumerate(bm25_ids):
        scores[d] = scores.get(d, 0.0) + w_bm25 / (k + rank + 1)
    return sorted(scores, key=lambda d: -scores[d])

vector = ["意味で近い A", "B", "C"]
bm25 = ["型番が一致 D", "B", "E"]
print("重みが同じ    :", weighted_rrf(vector, bm25))
print("BM25 を 3 倍  :", weighted_rrf(vector, bm25, w_bm25=3.0))
print("ベクトルを 3 倍:", weighted_rrf(vector, bm25, w_vec=3.0))
```

```text
# 出力
重みが同じ    : ['B', '意味で近い A', '型番が一致 D', 'C', 'E']
BM25 を 3 倍  : ['B', '型番が一致 D', 'E', '意味で近い A', 'C']
ベクトルを 3 倍: ['B', '意味で近い A', 'C', '型番が一致 D', 'E']
```

- 重みが同じなら、両方に出る `B` が 1 位。
- BM25 を 3 倍にすると、**型番が一致した D** が、A を抜いて **2 位**に上がる(B は両方に出ているので、1 位のまま)。D を 1 位にするには、BM25 の重みを、さらに大きくする(または、B のように両方に出ない文書だけを対象にする)。
- 本物に入れるなら: `_rrf_merge` に引数を足す(既定は 1.0 = 今と同じ)→ `search` に渡す → **質問に型番らしい語があるか**を判断する規則 → テストを足す → **評価する**(下)。

### 評価は、どうするか

この道具には、**検索の精度を測る仕組みが、まだありません**。重みを変えて「良くなった」と言うには、**質問と正解の文書の組**(評価セット)が要ります。

1. 自分の vault から、質問を 20〜30 個作り、正解のファイルを決める(型番を含むものと、含まないもの)。
2. 各質問で、上位 5 件に正解が入っている割合(**Recall@5**)を、変更の前後で比べる。
3. **型番の質問が良くなり、それ以外が悪くならない**ことを確かめる。

## 確認問題

1. `test_vector_database.py` の 2 件が失敗するのは、なぜですか。どう直しますか。
2. `EmbeddingGenerator._add_prefix(None, ...)` と呼べるのは、なぜですか。
3. 「チャンクの数は 3 になる」というテストより、「どのチャンクも空でない」というテストが好まれるのは、なぜですか。
4. 検索を改良したとき、「良くなった」と言うために要るものは。

## 解答

1. PostgreSQL 時代の `EMBEDDING_DIM`・テーブル作成を前提にしたテストが、ChromaDB 版のコードに残っているから。現在の仕様(namespace・BM25)に合わせて**書き直す**か、不要なら削除する。
2. そのメソッドが `self` を使わないので、モデルを持つインスタンスが要らない。
3. チャンクの数は、サイズや区切りの調整で変わるが、「空でない」は、実装が変わっても**成り立つべき性質**だから。
4. **評価セット**(質問と正解の組)と、変更の前後で測った数字。

## まとめ

- 検索の核(チャンク・RRF・トークン化・namespace)は、モデルなしでテストできる。**性質**を書く。
- 古いテストは、実態とずれて失敗し続けると、本物の失敗を見逃させる。直すか消す。
- 検索の改良は、**評価セット**で測ってから採用する。
- ここから先は、[学習資料](../learn/index.md)(保守・拡張の実務編)へ。
