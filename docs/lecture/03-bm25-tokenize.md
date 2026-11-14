# 第 3 回 語で探す(BM25)と、日本語のトークン化

> 所要時間の目安: 3 時間 / 前提: 第 2 回

## この回のゴール

- **BM25** が、どんな考え方で「語の一致」に点を付けるか説明できる。
- ベクトル検索が**苦手なもの**(型番・固有名詞)を、BM25 がどう補うか分かる。
- 日本語を**語に分ける(トークン化)**手順と、SudachiPy が無いときの代替を説明できる。
- `_tokenize` の出力を読んで、なぜ**英数字を別に拾う**のか分かる。

## 1. ベクトル検索の弱点

意味検索は、`BTQ-116` や `FR-3` のような**型番・ゲーム ID・略語**に弱い。これらは意味を持たないので、ベクトルでは「近い」が当てにならないからです。
こういうものは、**同じ語が出てくるか**という、古典的な語の一致で探す方が確実です。これが **BM25** です。

## 2. BM25 の考え方

BM25 は、クエリの各語について、次を掛け合わせて足します。

| 要素 | 考え方 |
|---|---|
| **語の珍しさ(IDF)** | 多くの断片に出る語(「の」「です」)は軽く、**少数にしか出ない語**(`btq-116`)は重く |
| **出現回数(TF)の飽和** | 1 回より 2 回の方が良いが、**10 回と 11 回はほぼ同じ**(増え方が頭打ちになる) |
| **長さの補正** | 長い断片は、語が出やすいので、**長さで割り引く** |

```python
# 実行できる
from rank_bm25 import BM25Okapi

docs = [
    "BTQ-116 の攻略手順を説明します",
    "シェーダーの学び方の基礎",
    "BTQ-200 の攻略と BTQ-116 の比較",
]
tokenized = [d.lower().replace("の", " ").split() for d in docs]
bm25 = BM25Okapi(tokenized)
scores = bm25.get_scores(["btq-116"])
for d, s in zip(docs, scores):
    print(f"{s:6.3f}  {d}")
```

```text
# 出力
 0.113  BTQ-116 の攻略手順を説明します
 0.000  シェーダーの学び方の基礎
 0.083  BTQ-200 の攻略と BTQ-116 の比較
```

`btq-116` を含む 1 つ目・3 つ目だけに点が付き、含まない 2 つ目は **0**。意味は見ていません。

## 3. 日本語は「語」に分ける必要がある

英語は空白で語に分かれますが、日本語は分かれません。BM25 は語を単位に数えるので、**日本語を語に分ける(トークン化)**必要があります。

このサーバーは、**SudachiPy**(日本語の形態素解析器)を使います。

```python
# 引用: src/vector_database.py::VectorDatabase._tokenize
def _tokenize(self, text: str) -> list[str]:
    """
    日本語テキストをトークン列に変換。
    SudachiPy が使えればそれを使い、なければ regex fallback。
    """
    # SudachiPy 使用可否を初回だけ確認
    if self._use_sudachi is None:
        try:
            from sudachipy import dictionary as _sd
            dic = _sd.Dictionary()
            self._sudachi = dic.create()
            self._use_sudachi = True
        except Exception:
            self._use_sudachi = False

    tokens: list[str] = []

    if self._use_sudachi and self._sudachi is not None:
        stop_pos = {"助詞", "助動詞", "記号", "補助記号", "空白"}
        try:
            morphs = self._sudachi.tokenize(text)
            for m in morphs:
                pos = m.part_of_speech()[0]
                if pos in stop_pos:
                    continue
                form = m.dictionary_form()
                if len(form) > 1:
                    tokens.append(form)
        except Exception:
            pass

    # 英数字 / ゲームID / モデル名（BTQ-116, FR-3, TC-8 など）は常に追加
    alpha = re.findall(r"[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*", text)
    tokens.extend(t.lower() for t in alpha if len(t) > 1)

    # SudachiPy が使えない場合は CJK 2文字以上 + 英数字で代替
    if not self._use_sudachi:
        cjk = re.findall(r"[぀-ヿ一-鿿]{2,}", text)
        tokens.extend(cjk)

    return list(dict.fromkeys(tokens)) if tokens else text.split()
```

読むポイント:

1. **初回だけ** Sudachi が使えるか確かめる(`_use_sudachi`)。使えなければ、あとの代替に回る。
2. 助詞・助動詞・記号・空白は**除く**(`stop_pos`)。検索の役に立たない。
3. **辞書形**(`dictionary_form`)に直す(「学び」→「学ぶ」)。活用形が違っても同じ語になる。
4. **1 文字の語は捨てる**(ノイズが多い)。
5. **英数字の語は、別の正規表現で必ず追加する**(`BTQ-116` のような、ハイフンつきの型番を、そのまま 1 語として拾う)。小文字にそろえる。
6. Sudachi が無いときは、**かな・漢字の 2 文字以上の連なり**で代替する。空白・句読点で区切られた**連なり全体が 1 語**になる(「日本語の検索」は 1 語。助詞でも分けない)ので、**粗く**、語の一致は当たりにくくなる。
7. 重複を除く(`dict.fromkeys`)。語が 1 つも取れなければ、空白で分けた結果を返す。

```python
# 実行できる
from src.vector_database import VectorDatabase

vd = VectorDatabase({"chroma_path": "./data/chroma_doc_demo"})
for text in ["Unity のシェーダーを学ぶ(BTQ-116)", "これは、とても面白い本でした", "FR-3 と TC-8"]:
    print(text, "→", vd._tokenize(text))
print("Sudachi を使っている:", vd._use_sudachi)
```

```text
# 出力
Unity のシェーダーを学ぶ(BTQ-116) → ['unity', 'シェーダー', '学ぶ', 'btq', '116', 'btq-116']
これは、とても面白い本でした → ['これ', 'とても', '面白い']
FR-3 と TC-8 → ['Fr', 'TC', 'fr-3', 'tc-8']
Sudachi を使っている: True
```

- `BTQ-116` から、Sudachi が `btq`・`116` を、正規表現が `btq-116` を拾う(**両方**入る)。検索で、`btq-116` と書いても、`btq 116` と書いても当たる。
- 助詞(「は」「の」)は落ちる。ただし、「これ」(代名詞)・「とても」(副詞)は**残る**(除くのは助詞・助動詞・記号・空白だけ)。BM25 の IDF が、どこにでもある語の重みを下げる。
- **英字の大文字・小文字は、そろわない**: `FR-3` から、Sudachi は `Fr`・`TC`(元の綴りに近い形)を、正規表現は `fr-3`・`tc-8`(小文字)を返す。索引も検索も、同じ `_tokenize` を通すので、**対で一致する**が、`fr` で探しても `Fr` とは当たらない(型番の全体 `fr-3` が当たる)。

## 4. 索引の保存と更新

BM25 の索引は、**namespace ごと**に `data/chroma/bm25/<namespace>.pkl`(pickle)に保存されます。

- 文書を足す・消す・クリアするたびに、**同期して更新**する(`batch_insert_documents` などが、BM25 も作り直す)。
- 索引が無ければ、ChromaDB の内容から**再構築**する(`_rebuild_bm25_from_chroma`)。

**pickle は、信頼できないファイルを読むと、任意のコードを実行されうる**形式です。この索引は、**自分で作ったものだけ**を読む前提です(他人からもらった `.pkl` を置かない)。

## 確認問題

1. `BTQ-116` を意味検索だけで探すと、なぜ当たりにくいのですか。
2. BM25 で、「の」のような、どこにでもある語の重みは、大きいですか小さいですか。
3. 「学び」と「学ぶ」を同じ語として扱うのは、どの工夫ですか。
4. Sudachi が無い環境では、日本語は、どう語に分けますか。

## 解答

1. 型番は意味を持たず、埋め込みモデルが「近さ」を測る材料が無いから(似た見た目の別の型番とも、近くなってしまう)。
2. 小さい(IDF が低い)。ほとんどの断片に出るので、区別の役に立たない。
3. **辞書形**(`dictionary_form`)に直す。
4. かな・漢字の **2 文字以上の連なり全体**を、そのまま 1 語として使う(粗い代替。助詞でも分けない)。英数字は、正規表現で拾う。

## まとめ

- BM25 は、語の一致を、珍しさ・頭打ちの出現回数・長さの補正で点にする。型番・固有名詞に強い。
- 日本語は、Sudachi で語に分け、助詞を除き、辞書形に直す。英数字(型番)は別に拾う。
- BM25 の索引は pickle で保存する。**自分で作ったものだけ読む**。
- 次の回は、ベクトル検索と BM25 を、**RRF** で合わせる。
