# Attacker 03 CODE INSPECTOR - コード精査

Bug Bounty用のコード脆弱性検査を実行します。

Usage: `/a03_code`

このコマンドは環境変数から必要な情報を取得します：
- SOURCE_PATH: 解析対象のSolidityコードルートパス

必要なファイル：
- outputs/00_AST.json
- outputs/00_callgraph.json
- outputs/02_SPEC.json

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/03_CODE_INSPECTOR.md', 'utf8');
%>

<%= promptContent %>