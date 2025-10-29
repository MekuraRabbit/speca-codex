#!/usr/bin/env bash
set -eu

# Remove the nested git metadata so this repo can be vendored elsewhere
rm -rf security-agent/.git

cp -a "./security-agent/prompts/." "${HOME}/.codex/prompts"
