# WHITEHAT 02 AUDITMAP - 監査注釈とマップ更新

ソースコードに@audit/@audit-ok注釈を追加し、監査マップを更新します。

Usage: `/02_auditmap <target_folder> [audit_order_file]`
Example: `/02_auditmap crates/net/` or `/02_auditmap crates/net/ outputs/WHITEHAT_01b_AUDITMAP_ORDER.json`

Arguments:
- target_folder: 監査対象のフォルダパス
- audit_order_file: 監査順序ファイル（省略時: security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json）

---

<% 
// Parse arguments
const args = input.trim().split(/\s+/);
const targetFolder = args[0];
const auditOrderFile = args[1];

// Ensure folder has trailing slash
const normalizedFolder = targetFolder.endsWith('/') ? targetFolder : targetFolder + '/';

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/02_AUDITMAP.md', 'utf8');

// Replace template variables
const processedContent = promptContent
  .replace(/\{\{TARGET_FOLDER\}\}/g, normalizedFolder)
  .replace(/\{\{AUDIT_ORDER_FILE\}\}/g, auditOrderFile);
%>

<%= processedContent %>
