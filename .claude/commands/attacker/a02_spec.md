# Attacker 02 SPEC - システム仕様分析

Bug Bounty用のシステム仕様分析を実行します。

Usage: `/a02_spec`

このコマンドは環境変数から必要な情報を取得します：
- DOCUMENT_URL: 解析対象のドキュメントURL
- BOUNTY_URL: Bug BountyプログラムのURL

---

<% 
// Read the original prompt file content
const fs = require('fs');
const promptContent = fs.readFileSync('prompts/attacker/02_SPEC.md', 'utf8');
%>

<%= promptContent %>