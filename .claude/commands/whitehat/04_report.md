# WHITEHAT 04 REPORT - Bug Bountyレポート生成

Ethereum Foundation向けのBug Bountyレポートを生成します。

Usage: `/04_report <vuln_name> <ut_path> <it_path>`
Example: `/04_report DoSUnboundedImport crates/net/network/src/transactions/poc_dos_unbounded_import.rs crates/net/network/tests/it/poc_tx_import.rs`

Arguments:
- vuln_name: 脆弱性名
- ut_path: Unit TestのPoCファイルパス
- it_path: Integration TestのPoCファイルパス（オプション: "none"を指定可能）

---

<% 
// Parse arguments with support for quoted strings
const args = input.trim().match(/(?:[^\s"]+|"[^"]*")+/g);
const vulnName = args[0];
const pocTestFile = args[1];

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/04_REPORT.md', 'utf8');

// Replace template variables
const processedContent = promptContent
  .replace(/\{\{VULN_NAME\}\}/g, vulnName)
  .replace(/\{\{POC_TEST_FILE\}\}/g, pocTestFile)

%>

<%= processedContent %>
