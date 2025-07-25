# Attacker 07 REPORT - セキュリティレポート作成

Bug Bountyレポートを生成します。

Usage: `/a07_report`

必要なファイル：
- docs/report_templete_cantina.md
- outputs/05_ATTACK_SCENARIOS.json
- outputs/06_POC.json
- outputs/01_SCOPE.md

出力：
- outputs/07_REPORT_<index>_<title_snake_case>.md (各成功シナリオ)

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/07_REPORT.md', 'utf8');
%>

<%= promptContent %>