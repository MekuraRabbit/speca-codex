# Attacker 03b MUTATION TESTS - 再帰的監査

Mutation testingによる再帰的脆弱性検査を実行します。

Usage: `/a03b_mutation`

このコマンドは環境変数から必要な情報を取得します：
- SOURCE_PATH: Solidityコードルートパス

必要なファイル：
- outputs/00_AST.json
- outputs/00_callgraph.json
- outputs/02_SPEC.json
- contracts/test/**/*.t.sol

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/03b_MUTATION_TESTS.md', 'utf8');
%>

<%= promptContent %>