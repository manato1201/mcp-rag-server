# 7. 基礎の補強(言語・設計思想・アルゴリズム・用語)

講義と学習資料の**前提になっている知識**を、ここで補います。「Python の基本」「検索・AI の用語」を、**このサーバーのコードで実際に使われている形**で、動かして確かめます。

## 1. 言語の基礎: mcp-rag-server で使う Python

### 1.1 型ヒント(`List`・`Dict`・`Optional`)と `dict.get`

`List[str]` は「文字列のリスト」、`Optional[dict]` は「辞書か、無いこと」。`dict.get(キー, 既定値)` は、**キーが無くても落ちず**に既定値を返す(RRF のスコア集計で使う)。

```python
# 実行できる
from typing import Dict, List, Optional


def first_chunk(chunks: List[str]) -> Optional[str]:
    return chunks[0] if chunks else None            # 空なら None(落ちない)


scores: Dict[str, float] = {}
for doc_id in ["a", "b", "a"]:
    scores[doc_id] = scores.get(doc_id, 0.0) + 1.0   # 無ければ 0.0 から数える
print(scores)
print(first_chunk([]), first_chunk(["x", "y"]))
```

```text
# 出力
{'a': 2.0, 'b': 1.0}
None x
```

### 1.2 `sorted(key=..., reverse=True)` と `lambda`

「**何で並べるか**」を `key` に渡す。`lambda d: scores[d]` は、**その場で作る小さな関数**。降順は `reverse=True`。

```python
# 実行できる
scores = {"A": 0.016, "B": 0.032, "C": 0.015}
ranked = sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)
print(ranked)
print("上位 2 件:", ranked[:2])

records = [{"id": "x", "n": 3}, {"id": "y", "n": 1}]
print(sorted(records, key=lambda r: r["n"]))
```

```text
# 出力
['B', 'A', 'C']
上位 2 件: ['B', 'A']
[{'id': 'y', 'n': 1}, {'id': 'x', 'n': 3}]
```

### 1.3 ファイル・`pathlib`・ハッシュ(`with open`)

`with open(path, "rb") as f:` は、**終わると必ず閉じる**書き方。`rb` は**バイト**で読む。ファイルの**内容のハッシュ**(SHA-256)を、**変更の検知**に使う(同じ内容なら、同じハッシュ)。

```python
# 実行できる
import hashlib
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    path = Path(d) / "note.md"
    path.write_text("# メモ\nRAG の勉強", encoding="utf-8")

    def file_hash(p: Path) -> str:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    before = file_hash(path)
    print("同じ内容なら同じ:", before == file_hash(path))
    path.write_text("# メモ\nRAG の勉強(追記)", encoding="utf-8")
    print("変更すると変わる:", before != file_hash(path), " 拡張子:", path.suffix, " 名前:", path.stem)
```

```text
# 出力
同じ内容なら同じ: True
変更すると変わる: True  拡張子: .md  名前: note
```

### 1.4 例外とログ: 「失敗しても、全体を止めない」

1 つのファイルの読み込みに失敗しても、**他のファイルの処理は続ける**。例外を `try / except` で受け、**ログに残して**次へ進む。**黙って握りつぶさない**(ログに理由を残す)。

```python
# 実行できる
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", force=True)
logger = logging.getLogger("indexer")


def process(name: str) -> int:
    if name.endswith(".bad"):
        raise ValueError("読めない形式")
    return len(name)


done = []
for name in ["a.md", "b.bad", "c.md"]:
    try:
        done.append(process(name))
    except ValueError as error:
        logger.warning("%s をスキップ: %s", name, error)      # 理由を残して、次へ
print("処理できた:", done)
```

```text
# 出力
処理できた: [4, 4]
```

## 2. 設計思想

| 原則 | 意味 | mcp-rag-server のどこに出るか | 破るとどうなるか |
|---|---|---|---|
| **薄い層を重ねる** | MCP(口)/ サービス / ベクトル DB を分ける | `mcp_server.py` → `rag_service.py` → `vector_database.py` | 口の変更が、検索の中身まで波及する |
| **2 つの検索を合わせる(ハイブリッド)** | 意味検索と語の検索の、**弱点を補い合う** | `_rrf_merge` | 型番や固有名詞を取りこぼす / 言い換えに弱い |
| **順位で合わせる(点数で合わせない)** | 点数の尺度が違うものを、順位で公平に混ぜる | RRF(`1/(k+順位)`) | 尺度の大きい方が、一方的に勝つ |
| **差分で更新する** | 変わったファイルだけを、索引し直す | ファイルのハッシュ・レジストリ | 毎回、全部を作り直して遅い |
| **名前空間で分ける** | 資料の種類ごとに、検索の対象を分ける | `_namespace_from_path` | 無関係な資料が混ざる |
| **前後の文脈を足せる** | 断片だけでなく、隣の断片も返せる | `get_adjacent_chunks` | 断片だけでは意味が通らない |
| **失敗しても止めない** | 1 ファイルの失敗で、全体を止めない | 例外 + ログ | 1 件の壊れたファイルで、索引が作れない |

**注意(読んで見つけたこと)**: `calculate_file_hash` は、**読み込みに失敗すると、時刻から作った値を返す**。失敗が**毎回違う「ハッシュ」**になり、変更ありと判定されて**毎回索引し直される**(失敗を、成功のふりをして返している)。

## 3. 関数・アルゴリズム

| 名前 | 場所 | 何をする | 計算量・注意 |
|---|---|---|---|
| **チャンク分割(重なりつき)** | `split_into_chunks` | `chunk_size` 文字ずつ切り、**文の途中で切らない**よう、次の改行・句点まで延ばす。`overlap` 文字を重ねる | O(文字数)。重なりで、**境界の文が両方に入る** |
| **BM25** | `_bm25_search` | 語の出現数・文書の長さ・語の珍しさ(IDF)で点を付ける | 索引の語数に比例 |
| **RRF** | `_rrf_merge` | 2 つの順位から `1/(k+順位)` を足す(k = 60) | O(結果数 log 結果数) |
| **コサイン類似度(ベクトル検索)** | ChromaDB | 埋め込みベクトルの向きの近さ | 近似探索で高速化 |
| **SHA-256** | `calculate_file_hash` | 内容から、固定長の値を作る | O(ファイルの大きさ) |

```python
# 実行できる
from src.document_processor import DocumentProcessor

processor = DocumentProcessor()
text = ("Sentence one. " * 12) + "\n" + ("Sentence two. " * 12)
chunks = processor.split_into_chunks(text, chunk_size=60, overlap=15)
print("チャンク数:", len(chunks))
print("各チャンクの長さ:", [len(c) for c in chunks])
print("隣のチャンクは、重なる:", chunks[0][-10:] in chunks[1])
print("空文字列:", processor.split_into_chunks("", 60, 15))
```

```text
# 出力
チャンク数: 6
各チャンクの長さ: [169, 60, 60, 60, 48, 15]
隣のチャンクは、重なる: True
空文字列: []
```

- **`chunk_size` が小さい**と、断片は精密だが**文脈が失われる**。**大きい**と、文脈は残るが**検索が粗く**なる。`overlap` は、その**境目の取りこぼし**を減らす。

## 4. IT・AI の用語の補強

| 用語 | 意味 | このサーバーでの出番 |
|---|---|---|
| **LLM(大規模言語モデル)** | 大量の文章で学んだ、文章を作る AI | 利用側(Claude など) |
| **RAG** | 質問に関係する資料を**先に検索**し、AI に渡して答えさせる | 全体 |
| **ハルシネーション** | AI が、事実でないことをもっともらしく答えること | RAG で、出典を添えて減らす |
| **コンテキストウィンドウ** | AI が一度に読める量の上限 | 断片(チャンク)に分ける理由 |
| **埋め込み(embedding)** | 文章を、意味が近いほど近くなる**数のベクトル**にしたもの | `embedding_generator.py` |
| **ベクトル DB(ChromaDB)** | ベクトルを保存し、近いものを探すデータベース | `vector_database.py` |
| **top-k** | 上位 k 件を返すこと | 検索の件数 |
| **トークン化(tokenize)** | 文章を、検索の単位(語・文字)に分けること | 日本語は語の切れ目が無いので、工夫が要る(BM25) |
| **MCP / JSON-RPC / stdio** | AI がツールを呼ぶ取り決め / その呼び出しの形式 / 標準入出力でやりとりする方式 | `mcp_server.py` |
| **ツール(tool)** | AI が呼べる関数(検索・索引など) | `rag_tools.py` |
| **名前空間(namespace)** | 資料の種類ごとの区画 | 検索の対象の絞り込み |
| **差分索引(incremental)** | 変わった所だけ更新する | ハッシュで検知 |
| **スキーマ(JSON Schema)** | データの形の決まり | ツールの引数の定義 |

## 確認問題

1. `dict.get(キー, 0.0)` を使う利点は何ですか。
2. 1 ファイルの失敗で、索引全体を止めない作りにするには、何をしますか。
3. RRF が、点数ではなく**順位**で混ぜるのは、なぜですか。
4. `chunk_size` を大きくすると、検索の何が良くなり、何が悪くなりますか。

## 解答

1. キーが無くても落ちず、既定値から数え始められる。
2. 例外を受けて、ログに理由を残し、次のファイルへ進む(黙って握りつぶさない)。
3. ベクトル検索と BM25 は、点数の尺度が違うので、順位なら公平に混ぜられるから。
4. 文脈が残る(良い)。検索が粗くなり、関係ない部分も混ざる(悪い)。
