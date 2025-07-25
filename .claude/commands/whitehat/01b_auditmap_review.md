# WHITEHAT 01b AUDITMAP ORDER Generator

Generate an ordered audit map for security review of a specific target folder.

Usage: `/01b_auditmap_review <target_folder>`

Arguments:
- target_folder: The folder path to analyze (relative to the project root)

---

<% 
// Parse the argument
const args = input.trim().split(/\s+/);
const targetFolder = args[0];

// Read the original prompt content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/whitehat/01_AUDITMAP_ORDER.md', 'utf8');

// Replace the template variable
const processedContent = promptContent.replace(/\{\{TARGET_FOLDER\}\}/g, targetFolder);
%>

<%= processedContent %>
