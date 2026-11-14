"""docs/diagrams/ の構成図(SVG)を作る。直すときは、ここを直して `python tools/make_diagrams.py` を実行する。

  architecture.svg   全体の構成(MCP ホスト・サーバー・データ・索引の作り手)

部品は tools/svgkit.py。座標は手で決める。決まり: ①矢印はカードの横から出入り(カードの下には文字がある)
②縦に渡るときは、カードの間のすき間を通る ③流れの説明は、図に詰めず、本文の Mermaid(シーケンス図)に書く。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from svgkit import Diagram  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "diagrams"


def architecture() -> Diagram:
    d = Diagram(1640, 900, "MCP RAG Server の構成",
                "Claude Desktop などの MCP ホストが、標準入出力の JSON-RPC でこのサーバーを呼ぶ。サーバーは、クエリをベクトル化し、ChromaDB のベクトル検索と BM25 の語の検索を、RRF で合わせて返す。"
                "索引は、CLI か watchdog の自動インデックスが、ドキュメントの変更を見て作り直す。")
    d.text(40, 44, "MCP RAG Server — 構成", cls="hd")
    d.text(40, 66, "青=検索の流れ / 灰の破線=索引を作る側 / すべてこの PC の中(外へ送らない)", cls="note")

    host = d.card(100, 330, "user", "MCP ホスト", "Claude Desktop など")
    d.group(220, 100, 840, 520, "MCP RAG SERVER — PYTHON (src/)", color="teal")
    srv = d.card(330, 220, "terminal", "mcp_server", "JSON-RPC over stdio")
    tools = d.card(560, 220, "extension", "rag_tools", "search\nget_document_count")
    svc = d.card(790, 220, "gear", "rag_service", "索引と検索の統括")
    dp = d.card(330, 440, "doc", "document_processor", "markitdown・チャンク分割\n差分(ファイルのハッシュ)")
    emb = d.card(560, 440, "wave", "embedding_generator", "multilingual-e5\n(クエリ / 文書の接頭辞)")
    vdb = d.card(790, 440, "db", "vector_database", "Chroma + BM25 + RRF\nSudachi で日本語")

    d.arrow([host.right, (180, 330), (180, 220), srv.left], "tools/call", at=2, dy=-10)
    d.arrow([srv.right, tools.left], "")
    d.arrow([tools.right, svc.left], "")
    for tgt in (dp, emb, vdb):
        d.arrow([svc.right, (930, 220), (930, 350), (tgt.cx, 350), (tgt.cx, tgt.top[1])], "")

    d.group(1160, 100, 440, 520, "LOCAL DATA — ファイル", color="gray")
    d.card(1260, 220, "folder", "SOURCE_DIR", "Obsidian vault など\n最初の階層 = namespace")
    d.card(1480, 220, "doc", "processed/", "変換済みの Markdown\nfile_registry.json")
    chroma = d.card(1260, 440, "db", "data/chroma/", "コレクション\n(namespace ごと)")
    d.card(1480, 440, "list", "bm25/*.pkl", "BM25 の索引\n(namespace ごと)")
    d.arrow([vdb.right, (1100, 440), (1100, 460), (chroma.left[0], 460)], "保存・検索", kind="primary", at=1, dy=-10)

    d.group(220, 700, 1380, 160, "INDEXING — 索引を作る(利用者・自動)", color="purple")
    cli = d.card(420, 770, "terminal", "cli.py index", "全部 / --incremental")
    auto = d.card(700, 770, "clock", "auto_index.py", "watchdog が保存を監視")
    d.card(980, 770, "check", "期限(expires)", "frontmatter で古い文書を整理")
    d.arrow([cli.right, auto.left], "", kind="secondary", both=True)
    d.arrow([(1030, 770), (1380, 770), (1380, 664)][0:1] + [(1060, 770), (1380, 770), (1380, 620)][1:], "rag_service.index_documents を呼ぶ", kind="secondary", at=0, dy=-10)
    return d


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture.svg").write_text(architecture().svg(), encoding="utf-8")
    print("wrote", OUT / "architecture.svg")


if __name__ == "__main__":
    main()
