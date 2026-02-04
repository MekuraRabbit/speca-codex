#!/usr/bin/env bash
set -euo pipefail

echo "Verifying and setting up MCP servers..."

SERVERS=("tree_sitter" "serena" "semgrep")
COMMANDS=(
  "uv run --from git+https://github.com/wrale/mcp-server-tree-sitter mcp-server-tree-sitter"
  "uv run --from git+https://github.com/oraios/serena serena"
  "npx -y @semgrep/mcp-server"
)

for i in "${!SERVERS[@]}"; do
  SERVER_NAME="${SERVERS[$i]}"
  SERVER_COMMAND="${COMMANDS[$i]}"

  if claude mcp list | grep -q "${SERVER_NAME}"; then
    echo "MCP server '${SERVER_NAME}' already registered."
  else
    echo "Registering MCP server '${SERVER_NAME}'..."
    claude mcp add --scope project --transport stdio "${SERVER_NAME}" -- ${SERVER_COMMAND}
  fi
done

echo
echo "Final MCP server list:"
claude mcp list

if [ -f ".mcp.json" ]; then
  echo
  echo "Contents of .mcp.json:"
  cat .mcp.json
else
  echo
  echo ".mcp.json not found. MCP servers might be registered at user scope."
fi
