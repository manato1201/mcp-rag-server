"""検索の核(チャンク分割・RRF・トークン化・namespace)のテスト。重いモデルも、ChromaDB の接続も使わない。"""

import os

import pytest

from src.document_processor import DocumentProcessor
from src.embedding_generator import EmbeddingGenerator
from src.vector_database import VectorDatabase


@pytest.fixture(scope="module")
def dp():
    return DocumentProcessor()


@pytest.fixture
def vd(tmp_path):
    return VectorDatabase({"chroma_path": str(tmp_path / "chroma")})  # connect() を呼ばないので、何も作られない


# ---- チャンク分割 ----
def test_empty_text_gives_no_chunks(dp):
    assert dp.split_into_chunks("") == []


def test_chunks_are_non_empty_and_cover_both_ends(dp):
    text = "第一の文です。第二の文です。第三の文です。\n第四の文です。" * 5
    chunks = dp.split_into_chunks(text, chunk_size=30, overlap=5)
    assert chunks and all(chunks)
    assert text.startswith(chunks[0]) and text.endswith(chunks[-1])


def test_chunks_extend_to_the_next_sentence_end(dp):
    chunks = dp.split_into_chunks("あ" * 20 + "。" + "い" * 20 + "。", chunk_size=10, overlap=0)
    assert chunks[0].endswith("。")  # 10 字で切らず、次の「。」まで延ばす
    assert len(chunks[0]) > 10


def test_neighbouring_chunks_overlap(dp):
    text = "ABCDEFGHIJ" * 20  # 区切り文字が無い: 延びずに、サイズで切れる
    chunks = dp.split_into_chunks(text, chunk_size=50, overlap=10)
    assert len(chunks) > 2
    assert chunks[0][-10:] == chunks[1][:10]


def test_chunking_always_terminates_even_with_large_overlap(dp):
    assert dp.split_into_chunks("あいうえお。" * 10, chunk_size=10, overlap=50)  # 進まないループにならない


# ---- RRF ----
def _doc(i):
    return {"document_id": i, "content": i, "file_path": "", "chunk_index": 0, "similarity": 0.0}


def test_rrf_puts_documents_found_by_both_searches_first():
    top = VectorDatabase._rrf_merge([_doc("a"), _doc("both")], [_doc("b"), _doc("both")], limit=3)
    assert [r["document_id"] for r in top][0] == "both"


def test_rrf_keeps_documents_found_by_only_one_search():
    merged = VectorDatabase._rrf_merge([_doc("v")], [_doc("w")], limit=5)
    assert {r["document_id"] for r in merged} == {"v", "w"}


def test_rrf_score_formula_and_limit():
    merged = VectorDatabase._rrf_merge([_doc("a"), _doc("b")], [_doc("a")], limit=1)
    assert len(merged) == 1
    assert merged[0]["document_id"] == "a"
    assert merged[0]["similarity"] == pytest.approx(1 / 61 + 1 / 61)  # k = 60・どちらも 1 位


# ---- トークン化 ----
def test_alphanumeric_model_numbers_are_kept_whole_and_lowercased(vd):
    tokens = vd._tokenize("Unity で BTQ-116 を調べる")
    assert "btq-116" in tokens and "unity" in tokens


def test_tokens_have_no_duplicates(vd):
    tokens = vd._tokenize("abc abc abc")
    assert len(tokens) == len(set(tokens))


def test_regex_fallback_when_sudachi_is_unavailable(vd):
    vd._use_sudachi = False  # 使えない場合を再現(初回の確認を飛ばす)
    tokens = vd._tokenize("日本語の検索 FR-3")
    assert "日本語の検索" in tokens  # かな・漢字の連なり全体が 1 語(助詞でも分けない。粗い代替)
    assert "fr-3" in tokens


# ---- namespace ----
def test_namespace_is_the_first_directory_and_hidden_ones_are_excluded(vd, monkeypatch):
    monkeypatch.setenv("SOURCE_DIR", "vault")
    assert vd._namespace_from_path("vault/tutorials/a.md") == "tutorials"
    assert vd._namespace_from_path("vault/readme.md") == "default"
    assert vd._namespace_from_path("vault/_templates/t.md") is None
    assert vd._namespace_from_path("vault/.obsidian/x.md") is None


# ---- 接頭辞(モデルを読み込まない) ----
def test_prefix_is_added_once():
    add = EmbeddingGenerator._add_prefix
    assert add(None, "text", "query: ") == "query: text"
    assert add(None, "query: text", "query: ") == "query: text"
    assert add(None, "text", "") == "text"


def test_environment_is_not_polluted():
    assert os.environ.get("SOURCE_DIR") != "vault"  # monkeypatch が、テストの後で元に戻している
