# Attacker 04 ATTACK SCENARIOS - 攻撃シナリオ作成

Bug Bounty用の攻撃シナリオを作成します。

Usage: `/a04_scenarios`

必要なファイル：
- outputs/00_AST.json
- outputs/00_callgraph.json
- outputs/02_SPEC.json
- outputs/03_CODE_INSPECTOR.json
- outputs/03b_CODE_INSPECTOR.json (optional)
- outputs/05_REVIEW.json (optional)
- outputs/01_SCOPE.json

出力：
- outputs/04_ATTACK_SCENARIOS.json

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/04_ATTACK_SCENARIOS.md', 'utf8');
%>

<%= promptContent %>