/**
 * VENDORED FILE — DO NOT EDIT FOR FORMATTING.
 *
 * Source:    https://github.com/ex-machina-co/opencode-anthropic-auth
 * Path:      src/constants.ts
 * Commit:    01c1548afb1318bdebc6f33a8b1e2f4e28c90edd
 * Retrieved: 2026-05-03
 * License:   MIT (see header below)
 *
 * Modifications from upstream:
 *   - None (verbatim copy).
 *
 * Refresh procedure: see cli/docs/VENDOR.md.
 *
 * ---------------------------------------------------------------------------
 * MIT License
 *
 * Copyright (c) 2026 Ex Machina
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 * ---------------------------------------------------------------------------
 */

export const CLIENT_ID = '9d1c250a-e61b-44d9-88ed-5944d1962f5e'

export const AUTHORIZE_URLS = {
  console: 'https://platform.claude.com/oauth/authorize',
  max: 'https://claude.ai/oauth/authorize',
} as const

export const CODE_CALLBACK_URL =
  'https://platform.claude.com/oauth/code/callback'

export const TOKEN_URL = 'https://platform.claude.com/v1/oauth/token'

export const OAUTH_SCOPES = [
  'org:create_api_key',
  'user:profile',
  'user:inference',
  'user:sessions:claude_code',
  'user:mcp_servers',
  'user:file_upload',
]

export const TOOL_PREFIX = 'mcp_'

export const REQUIRED_BETAS = [
  'oauth-2025-04-20',
  'interleaved-thinking-2025-05-14',
]

export const OPENCODE_IDENTITY_PREFIX = 'You are OpenCode'
export const CLAUDE_CODE_IDENTITY =
  "You are a Claude agent, built on Anthropic's Claude Agent SDK."

export const CCH_SALT = '59cf53e54c78'
export const CCH_POSITIONS = [4, 7, 20]
export const CLAUDE_CODE_VERSION = '2.1.87'
export const CLAUDE_CODE_ENTRYPOINT = 'sdk-cli'

export const USER_AGENT = 'claude-cli/2.1.87 (external, cli)'

/**
 * Anchors that identify paragraphs to remove from the system prompt.
 * Any paragraph (text between blank lines) containing one of these
 * strings is removed entirely.
 *
 * This is resilient to upstream rewording — as long as the anchor
 * string (typically a URL) still appears somewhere in the paragraph,
 * the removal works regardless of how the surrounding text changes.
 */
export const PARAGRAPH_REMOVAL_ANCHORS = [
  // Help/feedback block — references the OpenCode GitHub repo
  'github.com/anomalyco/opencode',
  // OpenCode docs guidance — references the OpenCode docs URL
  'opencode.ai/docs',
]

/**
 * Inline text replacements applied after paragraph removal.
 * These handle cases where "OpenCode" appears inside a paragraph
 * we want to keep (so we can't remove the whole paragraph), or exact
 * phrase fingerprints Anthropic's server-side classifier uses to
 * detect third-party agent CLIs.
 *
 * The "Here is some useful information about the environment you are
 * running in:" phrase ships verbatim in OpenCode's default system prompt
 * (and many other agent CLIs). When it reaches Anthropic in combination
 * with typical agent-orchestration context, /v1/messages responds with a
 * 400 invalid_request_error disguised as "You're out of extra usage."
 * Replacing the word "useful" (or removing it entirely) is enough to
 * unblock the request — we rewrite the sentence to a semantic equivalent
 * so the model still sees the env-block intro.
 *
 * This was isolated via bisection: starting from a failing 10KB system
 * prompt, we sliding-window-deleted 1KB chunks until the request passed,
 * then narrowed to a 400-byte span, then to this single sentence. Both
 * removing and rewording "useful" pass; swapping "Here is" → "Here's"
 * does NOT, confirming the filter looks at this specific phrase shape.
 */
export const TEXT_REPLACEMENTS: { match: string; replacement: string }[] = [
  { match: 'if OpenCode honestly', replacement: 'if the assistant honestly' },
  {
    match:
      'Here is some useful information about the environment you are running in:',
    replacement: 'Environment context you are running in:',
  },
]
