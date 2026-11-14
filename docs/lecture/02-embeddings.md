# 第 2 回 ベクトル(埋め込み)と意味の近さ

> 所要時間の目安: 3 時間 / 前提: 第 1 回

## この回のゴール

- 文章を**ベクトル**にする(埋め込み)と、**意味の近さを数で測れる**理由が分かる。
- **コサイン類似度**を、手計算で確かめられる。
- e5 系のモデルの**接頭辞**(`query: ` / `passage: `)が必要な理由と、コードでの扱いが分かる。
- ChromaDB で距離を類似度に直す(`1 - dist`)意味を説明できる。

## 1. 埋め込みとは

**埋め込みモデル**(ここでは sentence-transformers の `multilingual-e5-large`)は、文章を **1024 個の数の並び(ベクトル)**に変えます。
**意味が近い文章は、ベクトルが近く**なるように学習されています(「犬を飼う」と「ペットを迎える」が近い、など)。

- 同じ言葉を使っていなくても、**意味で**近い断片を探せる(**意味検索**)。
- 弱点: 固有名詞・型番・略語(`BTQ-116`)は、意味にならず、近さが当てにならない。**そこを BM25 で補う**(第 3〜4 回)。

## 2. コサイン類似度

2 つのベクトルの**向きの近さ**。1 に近いほど近い、0 で無関係。

```python
# 実行できる
import math

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

cat = [0.9, 0.1, 0.0]        # 3 次元の、ごく小さな例(本物は 1024 次元)
kitten = [0.8, 0.2, 0.1]
car = [0.0, 0.2, 0.9]
print("猫 と 子猫:", round(cosine(cat, kitten), 3))
print("猫 と 車  :", round(cosine(cat, car), 3))
print("全部 2 倍 :", round(cosine(cat, [x * 2 for x in cat]), 3))
```

```text
# 出力
猫 と 子猫: 0.984
猫 と 車  : 0.024
全部 2 倍 : 1.0
```

ChromaDB は、**距離**(`cosine` なら `1 - 類似度`)を返します。このサーバーは、`1.0 - dist` で**類似度**に直しています(`vector_database.py` の `search`)。

## 3. 接頭辞(プレフィックス)

e5 系のモデルは、学習のときに、文章の頭に **`query: `**(検索の質問)・**`passage: `**(検索される文書)を付けて学習されています。
**使うときも、同じ付け方**をしないと、精度が落ちます。

```python
# 引用: src/embedding_generator.py::EmbeddingGenerator._add_prefix
def _add_prefix(self, text: str, prefix: str) -> str:
    """
    テキストに適切なプレフィックスを追加する

    Args:
        text: 元のテキスト
        prefix: 追加するプレフィックス

    Returns:
        プレフィックス付きのテキスト
    """
    if not prefix:
        return text

    # プレフィックスが既に含まれているかチェック（大文字小文字を区別）
    if text.startswith(prefix):
        return text

    return f"{prefix}{text}"
```

- 接頭辞が空なら、何もしない(モデルによっては要らない)。
- **すでに付いていれば、重ねて付けない**(二重の `query: query: …` を防ぐ)。
- 文書は `EMBEDDING_PREFIX_EMBEDDING`、質問は `EMBEDDING_PREFIX_QUERY`(`.env`)で決める。e5 の既定は `query:` と `passage:`(README の設定例は、コロンの後ろに空白を入れない書き方)。

```python
# 実行できる
from src.embedding_generator import EmbeddingGenerator

add = EmbeddingGenerator._add_prefix            # モデルを読み込まずに、関数だけ呼ぶ(self を使わないため)
print(add(None, "シェーダーの学び方", "query: "))
print(add(None, "query: シェーダーの学び方", "query: "))     # すでに付いている
print(add(None, "シェーダーの学び方", ""))                  # 接頭辞なし
```

```text
# 出力
query: シェーダーの学び方
query: シェーダーの学び方
シェーダーの学び方
```

## 4. モデルの選び方

| モデル | 特徴 | 接頭辞 |
|---|---|---|
| `intfloat/multilingual-e5-large`(既定) | 多言語・1024 次元・精度が高い・重い | 要(`query: ` / `passage: `) |
| `cl-nagoya/ruri-v3-30m` | 日本語に特化・軽い・256 次元 | `検索クエリ:` / `検索文書:`(README の設定) |

**モデルを変えたら、索引を作り直す**(ベクトルの次元・意味の空間が違うので、混ぜられない)。

## 確認問題

1. 「猫」と「車」のベクトルで、コサイン類似度が小さくなるのは、なぜですか。
2. ベクトルの全成分を 2 倍にすると、コサイン類似度はどうなりますか。
3. `query: ` を付け忘れると、何が起きますか。
4. 埋め込みモデルを変えたとき、既存の索引は使えますか。

## 解答

1. 意味の違う言葉は、ベクトルの**向きが離れる**ように学習されているから(例では 0.0 に近い)。
2. 変わらない(向きだけを見る。第 3 回に近い性質)。
3. 学習時と違う入力になり、**検索の精度が落ちる**(エラーにはならない。気づきにくい)。
4. 使えない。次元・意味の空間が違うので、**クリアして作り直す**。

## まとめ

- 埋め込みは、意味が近い文章を、近いベクトルにする。近さはコサイン類似度。
- e5 系は、質問と文書で**接頭辞を使い分ける**。
- 型番・固有名詞には弱いので、BM25 で補う(次の回)。
- モデルを変えたら、索引を作り直す。
