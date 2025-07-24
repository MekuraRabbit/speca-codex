# WHITEHAT 03b POC INTEGRATION - 統合テストPoC生成

脆弱性を再現する統合レベルのPoCテストを作成します。

Usage: `/03b_poc_integration <ut_path> <it_path> <vuln_name>`
Example: `/03b_poc_integration crates/net/network/src/transactions/poc_dos_unbounded_import.rs crates/net/network/tests/it/poc_tx_import.rs DoSUnboundedImport`

Arguments:
- ut_path: ユニットテストPoCファイルパス
- it_path: 統合テストファイルパス
- vuln_name: 脆弱性名

---

<% 
// Parse arguments
const args = input.trim().split(/\s+/);
const integrationTestPath = args[0];
const integrationTestPath = args[1];
const vulnName = args[2];

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/03b_POC_INTEGRATION.md', 'utf8');

// Replace template variables
const processedContent = promptContent
  .replace(/\{\{UT_PATH\}\}/g, integrationTestPath)
  .replace(/\{\{IT_PATH\}\}/g, integrationTestPath)
  .replace(/\{\{VULN_NAME\}\}/g, vulnName);
%>

<%= processedContent %>
