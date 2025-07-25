# Attacker 05 REVIEW - レッドチーム査定

提出された攻撃シナリオをレビューします。

Usage: `/a05_review`

必要なファイル：
- outputs/04_ATTACK_SCENARIOS.json
- outputs/00_AST.json
- outputs/00_callgraph.json
- outputs/03_CODE_INSPECTOR.json
- outputs/01_SCOPE.json
- outputs/05_REVIEW.json (存在する場合)

出力：
- outputs/05_REVIEW.json

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/05_REVIEW.md', 'utf8');
%>

<%= promptContent %>