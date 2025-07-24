# WHITEHAT 03a POC UNIT - ユニットテストPoC生成

脆弱性を再現する最小限のPoCテストを作成します。

Usage: `/03a_poc_unit <vuln_name> <output_path>`
Example: `/03a_poc_unit DoSUnboundedImport "fn import_transactions(" crates/net/network/src/transactions/mod.rs:L1326 crates/net/network/src/transactions/poc_DoSUnboundedImport.rs`

Arguments:
- vuln_snippet: 脆弱性を含むコードスニペット
- output_path: 出力テストファイルパス

---

<% 
// Parse arguments
const args = input.trim().match(/(?:[^\s"]+|"[^"]*")+/g) || [];
const vulnName = args[0];
const outputPath = args[1];

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/03a_POC_UNIT.md', 'utf8');

// Replace template variables
const processedContent = promptContent
  .replace(/\{\{VULN_NAME\}\}/g, vulnName)
  .replace(/\{\{OUTPUT_TEST_PATH\}\}/g, outputPath);
%>

<%= processedContent %>
