#!/bin/sh
set -eu

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to format JSON output" >&2
  exit 1
fi

out_dir="security-agent/docs/ethereum"
mkdir -p "$out_dir"

while IFS=" " read -r repo filename; do
  [ -n "$repo" ] || continue

  tmp_file="$(mktemp)"

  if ! gh search issues --repo "$repo" --include-prs osaka --limit 200 --json body,closedAt,isPullRequest,labels,state,title,updatedAt,url >"$tmp_file"; then
    rm -f "$tmp_file"
    exit 1
  fi

  if ! jq '.' "$tmp_file" >"$out_dir/$filename"; then
    rm -f "$tmp_file"
    exit 1
  fi

  rm -f "$tmp_file"

done <<'REPOS'
ethereum/go-ethereum pr_geth.json
paradigmxyz/reth pr_reth.json
erigontech/erigon pr_erigon.json
hyperledger/besu pr_besu.json
NethermindEth/nethermind pr_nethermind.json
REPOS
