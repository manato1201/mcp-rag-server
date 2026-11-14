# 第 5 回 MCP と JSON-RPC(AI から道具を呼ぶ口)

> 所要時間の目安: 3 時間 / 前提: 第 0 回

## この回のゴール

- **JSON-RPC 2.0** のリクエスト・レスポンス・エラーの形を説明できる。
- MCP サーバーが、**標準入出力**で何を待ち、何を返すかを、コードで追える。
- 道具(tool)を**登録する**仕組みと、`tools/list`・`tools/call` の流れが分かる。
- **標準出力に余計なものを書いてはいけない**理由と、Windows の文字コードの落とし穴を説明できる。

## 1. JSON-RPC 2.0

**1 行 1 件の JSON** で、呼び出し(リクエスト)と結果(レスポンス)をやり取りします。

```text
→ {"jsonrpc":"2.0","id":1,"method":"tools/list"}
← {"jsonrpc":"2.0","id":1,"result":{"tools":[ ... ]}}
← {"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Method not found: x"}}
```

| 項目 | 意味 |
|---|---|
| `jsonrpc` | 常に `"2.0"` |
| `id` | 呼び出しと結果を対応づける番号(通知には無い) |
| `method` | 呼び出す名前 |
| `params` | 引数 |
| `result` / `error` | 成功 / 失敗(どちらか一方) |

標準のエラーコード: `-32700`(JSON が壊れている)・`-32600`(リクエストの形が不正)・`-32601`(メソッドが無い)・`-32603`(内部エラー)。

## 2. サーバーの本体

標準入力を 1 行ずつ読み、JSON にして、処理します。

```python
# 引用: src/mcp_server.py::MCPServer._handle_request
def _handle_request(self, request: Dict[str, Any]):
    """
    リクエストを処理します。

    Args:
        request: JSONリクエスト
    """
    # リクエストのバリデーション
    if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
        self._send_error(-32600, "Invalid Request", request.get("id"))
        return

    if "method" not in request:
        self._send_error(-32600, "Method not specified", request.get("id"))
        return

    # メソッドの取得
    method = request["method"]
    params = request.get("params", {})
    request_id = request.get("id")

    # メソッドの処理
    if method == "initialize":
        self._handle_initialize(params, request_id)
    elif method == "tools/list":
        self._handle_tools_list(request_id)
    elif method == "tools/call":
        self._handle_tools_call(params, request_id)
    elif method == "notifications/initialized":
        self._handle_notifications_initialized(params, request_id)
    elif method == "resources/list":
        self._handle_resources_list(request_id)
    elif method == "resources/templates/list":
        self._handle_resources_templates_list(request_id)
    else:
        # 登録されたツールを直接呼び出す
        if method in self.tool_handlers:
            try:
                result = self.tool_handlers[method](params)
                self._send_result(result, request_id)
            except Exception as e:
                self._send_error(-32603, f"Tool execution error: {str(e)}", request_id)
        else:
            self._send_error(-32601, f"Method not found: {method}", request_id)
```

- `jsonrpc` と `method` が無ければ、`-32600`。
- `initialize`(最初の握手)・`tools/list`(道具の一覧)・`tools/call`(道具の呼び出し)・`notifications/initialized` ほかを、**振り分け**る。
- 知らないメソッドは、登録された道具に**直接**呼べるか調べ、無ければ `-32601`。
- 道具が例外を出したら、`-32603` で返す(サーバー全体は止めない)。

```python
# 実行できる
import contextlib
import io
import json

from src.mcp_server import MCPServer

server = MCPServer()
server.register_tool(
    name="echo", description="受け取った文字を返す",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=lambda params: {"content": [{"type": "text", "text": params.get("text", "")}]},
)

def call(request):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):                    # サーバーが標準出力に書くものを捕まえる
        server._handle_request(request)
    return json.loads(buf.getvalue())

print(call({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"][0]["name"])
print(call({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "echo", "arguments": {"text": "こんにちは"}}}))
print(call({"jsonrpc": "2.0", "id": 3, "method": "nothing"})["error"])
print(call({"id": 4, "method": "tools/list"})["error"])
```

```text
# 出力
echo
{'jsonrpc': '2.0', 'result': {'content': [{'type': 'text', 'text': 'こんにちは'}]}, 'id': 2}
{'code': -32601, 'message': 'Method not found: nothing'}
{'code': -32600, 'message': 'Invalid Request'}
```

道具の `inputSchema` は **JSON Schema**で、AI に「どんな引数を渡せるか」を伝えます。`required` に無い引数は省略できる。

## 3. 道具を公開する

`rag_tools.py` が、`register_tool` で 2 つの道具を公開します。

| 道具 | 引数 | 返すもの |
|---|---|---|
| `search` | `query`(必須)・`limit`(5)・`with_context`(true)・`context_size`(1)・`full_document`(false) | ファイルごとにまとめた、断片のテキスト |
| `get_document_count` | なし | 索引の断片の数 |

返り値は、MCP の形 `{"content": [{"type": "text", "text": "..."}], "isError": ...}`。**エラーも、例外でなく `isError: true` の結果**で返します(AI が、エラーの文面を読んで、次の行動を決められる)。
索引が空のときは、「CLI でインデックス化してください」という**次にすることを書いた文**を返します。

## 4. 標準出力は、プロトコル専用

**標準出力(stdout)は、JSON-RPC の通り道**です。ここに、デバッグの `print` を書くと、**ホストが JSON として読めずに、壊れます**。
ログは、**標準エラー(stderr)とファイル**(`logs/mcp_rag_server.log`)に出します(`main.py` のログ設定)。

## 5. Windows の文字コード

Windows の標準入出力の既定の文字コードは **CP932** です。MCP は UTF-8 の JSON を送るので、**日本語のクエリが文字化け**し、`TextEncodeInput must be …` のようなエラーになります。
`main.py` の先頭が、標準入出力を **UTF-8 に包み直して**います。

```python
# 抜粋ファイル: src/main.py
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
```

- `line_buffering=True`: 1 行ごとに**すぐ送り出す**(溜め込むと、ホストが待ち続ける)。

## 確認問題

1. `id` が付いていないメッセージは、何ですか。
2. 道具の中で例外が出たとき、サーバーは止まりますか。
3. 検索の道具で、索引が空のとき、例外でなく文章を返すのは、なぜですか。
4. デバッグ用に `print("検索を開始")` を足すと、何が起きますか。

## 解答

1. **通知**(返事を要求しない)。`notifications/initialized` など。
2. 止まらない。`-32603`(Tool execution error)のエラーとして返して、次のリクエストを待つ。
3. AI が、**文面を読んで次の行動を決められる**ようにするため。例外だと、ホストには「失敗した」としか伝わらない。
4. stdout に混ざり、ホストが JSON として読めず、**接続が壊れる**。ログは stderr かファイルへ。

## まとめ

- MCP は、標準入出力の JSON-RPC。`initialize` → `tools/list` → `tools/call` が基本。
- 道具は `register_tool` で公開し、`inputSchema`(JSON Schema)で引数を伝える。エラーも結果で返す。
- stdout はプロトコル専用。ログは stderr・ファイルへ。Windows では UTF-8 に包み直す。
- 次の回は、索引を作る運用(差分・namespace・自動インデックス)。
