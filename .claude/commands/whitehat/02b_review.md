# WHITEHAT 02b AUDIT REVIEW - 監査レビューと検証

既存の@audit注釈をレビューし、検証します。

Usage: `/02b_review <target_folder> [audit_order_file]`
Example: `/02b_review crates/net/` or `/02b_review crates/net/ outputs/WHITEHAT_01b_AUDITMAP_ORDER.json`

Arguments:
- target_folder: レビュー対象のフォルダパス
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
const promptContent = fs.readFileSync('prompts/whitehat/02b_AUDITMAP_REVIEW.md', 'utf8');

// Replace template variables
const processedContent = promptContent
  .replace(/\{\{TARGET_FOLDER\}\}/g, normalizedFolder)
  .replace(/\{\{AUDIT_ORDER_FILE\}\}/g, auditOrderFile);
%>

<%= processedContent %>
