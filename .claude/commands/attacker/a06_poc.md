# Attacker 06 POC - エクスプロイト実装

有効な攻撃シナリオのPoCを作成します。

Usage: `/a06_poc`

必要なファイル：
- outputs/05_REVIEW.json
- ../contracts/src/ (Solidityコードベース)

出力：
- contracts/test/<index>_<title_snake_case>.t.sol (各シナリオ)
- outputs/06_POC.json

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/06_POC.md', 'utf8');
%>

<%= promptContent %>