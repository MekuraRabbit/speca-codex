# WHITEHAT 01 SPEC - 仕様書生成

プロジェクトの包括的な仕様書を生成します。

Usage: `/01_spec <target_folder>`
Example: `/01_spec ../contracts/docs`

Arguments:
- target_folder: 解析対象のドキュメントディレクトリパス

---

<% 
// Parse the argument
const args = input.trim().split(/\s+/);
const targetFolder = args[0];

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/01_SPEC.md', 'utf8');

// Replace the template variable
const processedContent = promptContent.replace(/\{\{TARGET_FOLDER\}\}/g, targetFolder);
%>

<%= processedContent %>
