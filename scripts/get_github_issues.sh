#!/bin/sh
set -eu

usage() {
  cat >&2 <<'USAGE'
Usage: get_github_issues.sh [options] [<repo1> ...]

Options:
  --repos list        Comma or space separated repositories (repeatable)
  --keywords list     Comma or space separated keywords; defaults to "fulu"
  --output path       Output JSON path; defaults to outputs/00_SIMILAR_ISSUES.json

Notes:
  - Writes a repository-keyed JSON object for reuse by later SPECA prompts.
USAGE
}

ensure_tools_present() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI is required" >&2
    exit 1
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required to format JSON output" >&2
    exit 1
  fi
}

append_repos_from_string() {
  input=$1
  sanitized=$(printf '%s' "$input" | tr ',\n\t' '   ')

  # shellcheck disable=SC2086
  for repo_entry in $sanitized; do
    [ -n "$repo_entry" ] || continue
    if [ -z "$repos" ]; then
      repos=$repo_entry
    else
      repos="$repos
$repo_entry"
    fi
  done
}

detect_input_mode() {
  case "$1" in
    https://github.com/*|http://github.com/*|git@github.com:*)
      printf 'url'
      ;;
    */*)
      printf 'slug'
      ;;
    *)
      echo "Invalid repository identifier: $1" >&2
      return 1
      ;;
  esac
}

normalize_repo() {
  input=$1
  expected=$2

  case "$expected" in
    slug)
      case "$input" in
        */*)
          repo=$input
          ;;
        *)
          echo "Expected owner/repo format but got: $input" >&2
          return 1
          ;;
      esac
      ;;
    url)
      case "$input" in
        https://github.com/*)
          repo=${input#https://github.com/}
          ;;
        http://github.com/*)
          repo=${input#http://github.com/}
          ;;
        git@github.com:*)
          repo=${input#git@github.com:}
          ;;
        *)
          echo "Expected GitHub URL but got: $input" >&2
          return 1
          ;;
      esac
      ;;
    *)
      echo "Unsupported normalization mode: $expected" >&2
      return 1
      ;;
  esac

  repo=${repo%.git}
  repo=${repo#/}

  case "$repo" in
    */*)
      printf '%s' "$repo"
      ;;
    *)
      echo "Invalid repository identifier after normalization: $input" >&2
      return 1
      ;;
  esac
}

parse_keywords() {
  raw=$1
  sanitized=$(printf '%s' "$raw" | tr ',\n\t' '   ')

  # shellcheck disable=SC2086
  set -- $sanitized

  if [ "$#" -eq 0 ]; then
    echo "At least one keyword must be provided" >&2
    return 1
  fi

  keywords_terms="$*"
}

keywords_input=""
keywords_terms=""
repos=""
out_file="outputs/00_SIMILAR_ISSUES.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keywords)
      shift || { usage; exit 1; }
      keywords_input=${1:-}
      if [ -z "$keywords_input" ]; then
        echo "Missing value for --keywords" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --keywords=*)
      keywords_input=${1#*=}
      if [ -z "$keywords_input" ]; then
        echo "Missing value for --keywords" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --repos)
      shift || { usage; exit 1; }
      if [ "$#" -eq 0 ]; then
        echo "Missing value for --repos" >&2
        usage
        exit 1
      fi
      repo_values=""
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --*|-*)
            break
            ;;
          *)
            if [ -z "$repo_values" ]; then
              repo_values=$1
            else
              repo_values="$repo_values $1"
            fi
            shift
            ;;
        esac
      done
      if [ -z "$repo_values" ]; then
        echo "Missing value for --repos" >&2
        usage
        exit 1
      fi
      append_repos_from_string "$repo_values"
      ;;
    --repos=*)
      repo_values=${1#*=}
      if [ -z "$repo_values" ]; then
        echo "Missing value for --repos" >&2
        usage
        exit 1
      fi
      append_repos_from_string "$repo_values"
      shift
      ;;
    --output)
      shift || { usage; exit 1; }
      out_file=${1:-}
      if [ -z "$out_file" ]; then
        echo "Missing value for --output" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --output=*)
      out_file=${1#*=}
      if [ -z "$out_file" ]; then
        echo "Missing value for --output" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -gt 0 ]; then
  for repo_arg in "$@"; do
    [ -n "$repo_arg" ] || continue
    append_repos_from_string "$repo_arg"
  done
fi

if [ -z "$repos" ]; then
  usage
  exit 1
fi

if [ -n "$keywords_input" ]; then
  parse_keywords "$keywords_input" || exit 1
fi

if [ -z "$keywords_terms" ]; then
  keywords_terms="fulu"
fi

ensure_tools_present

mkdir -p "$(dirname "$out_file")"

workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT INT TERM
collection="$workspace/data.jsonl"
: >"$collection"

expected_mode=""

printf '%s\n' "$repos" | while IFS= read -r repo_input; do
  [ -n "$repo_input" ] || continue

  inferred_mode=$(detect_input_mode "$repo_input") || exit 1

  if [ -z "$expected_mode" ]; then
    expected_mode=$inferred_mode
  elif [ "$inferred_mode" != "$expected_mode" ]; then
    echo "Mixed input formats detected. Please use consistent GitHub URLs or owner/repo slugs." >&2
    exit 1
  fi

  if ! repo=$(normalize_repo "$repo_input" "$expected_mode"); then
    continue
  fi

  tmp_json="$workspace/$(printf '%s' "$repo" | tr '/:' '__').json"

  repo_files=""
  for keyword in $keywords_terms; do
    keyword_file="$workspace/$(printf '%s' "$repo" | tr '/:' '__')__kw_$(printf '%s' "$keyword" | tr ' /:' '__').json"

    if ! gh search issues --repo "$repo" --include-prs --limit 200 --json body,closedAt,isPullRequest,labels,state,title,updatedAt,url -- "$keyword" >"$keyword_file"; then
      echo "Failed to fetch issues for $repo with keyword $keyword" >&2
      rm -f "$keyword_file"
      continue
    fi

    if [ -s "$keyword_file" ] && [ "$(jq 'length' "$keyword_file")" -gt 0 ]; then
      if [ -z "$repo_files" ]; then
        repo_files=$keyword_file
      else
        repo_files="$repo_files
$keyword_file"
      fi
    else
      rm -f "$keyword_file"
    fi
  done

  if [ -n "$repo_files" ]; then
    old_kw_ifs=$IFS
    IFS='
'
    # shellcheck disable=SC2086
    set -- $repo_files
    IFS=$old_kw_ifs

    if ! jq -s 'add | unique_by(.url)' "$@" >"$tmp_json"; then
      echo "Failed to combine keyword results for $repo" >&2
      continue
    fi
  else
    printf '[]' >"$tmp_json"
  fi

  if ! jq --arg repo "$repo" '{repo: $repo, items: .}' "$tmp_json" >>"$collection"; then
    echo "Failed to parse JSON for $repo" >&2
    continue
  fi

done

if ! jq -s 'reduce .[] as $entry ({}; .[$entry.repo] = $entry.items)' "$collection" >"$out_file"; then
  echo "Failed to build output JSON" >&2
  exit 1
fi

printf 'Wrote %s\n' "$out_file"
