const STORAGE_KEY_TOKEN = 'speca_github_token';
const STORAGE_KEY_REPO = 'speca_github_repo';
const API_BASE = 'https://api.github.com';

export function getToken(): string | null {
  return localStorage.getItem(STORAGE_KEY_TOKEN);
}

export function setToken(token: string): void {
  localStorage.setItem(STORAGE_KEY_TOKEN, token);
}

export function clearToken(): void {
  localStorage.removeItem(STORAGE_KEY_TOKEN);
}

export function getRepo(): string {
  return localStorage.getItem(STORAGE_KEY_REPO) ?? 'NyxFoundation/security-agent';
}

export function setRepo(repo: string): void {
  localStorage.setItem(STORAGE_KEY_REPO, repo);
}

export class GitHubApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'GitHubApiError';
    this.status = status;
  }
}

export async function githubFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = getToken();
  if (!token) {
    throw new GitHubApiError(401, 'GitHub token が設定されていません');
  }

  const repo = getRepo();
  const url = path.startsWith('http')
    ? path
    : `${API_BASE}/repos/${repo}${path}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github.v3+json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new GitHubApiError(res.status, `GitHub API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

export async function fetchFileContent(
  filePath: string,
  ref?: string,
): Promise<string> {
  const params = ref ? `?ref=${encodeURIComponent(ref)}` : '';
  const data = await githubFetch<{ content: string; encoding: string }>(
    `/contents/${filePath}${params}`,
  );

  if (data.encoding === 'base64') {
    return atob(data.content.replace(/\n/g, ''));
  }
  return data.content;
}

export async function fetchJsonFile<T>(
  filePath: string,
  ref?: string,
): Promise<T> {
  const content = await fetchFileContent(filePath, ref);
  return JSON.parse(content) as T;
}

// --- Workflow Dispatch ---

export interface WorkflowRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  html_url: string;
  head_branch: string;
  created_at: string;
  updated_at: string;
}

export async function fetchWorkflowRunById(runId: number): Promise<WorkflowRun> {
  return githubFetch<WorkflowRun>(`/actions/runs/${runId}`);
}

// --- Individual Phase Dispatch ---

export type PhaseId = '01a' | '01b' | '01e' | '02c' | '03' | '04';

export interface PhaseWorkflowConfig {
  workflowFile: string;
  workflowName: string;
}

export const PHASE_WORKFLOWS: Record<PhaseId, PhaseWorkflowConfig> = {
  '01a': { workflowFile: '01a-discovery.yml', workflowName: '01a. Discovery' },
  '01b': { workflowFile: '01b-subgraph.yml', workflowName: '01b. Subgraph Extraction' },
  '01e': { workflowFile: '01e-properties.yml', workflowName: '01e. Properties' },
  '02c': { workflowFile: '02c-enrich-code.yml', workflowName: '02c. Code Pre-resolution' },
  '03': { workflowFile: '03-audit-map.yml', workflowName: '03. Audit Map' },
  '04': { workflowFile: '04-audit-review.yml', workflowName: '04. Audit Review' },
};

export async function dispatchPhaseWorkflow(
  phaseId: PhaseId,
  ref: string,
  inputs: Record<string, string>,
): Promise<void> {
  const token = getToken();
  if (!token) {
    throw new GitHubApiError(401, 'GitHub token が設定されていません');
  }

  const repo = getRepo();
  const config = PHASE_WORKFLOWS[phaseId];
  const url = `${API_BASE}/repos/${repo}/actions/workflows/${config.workflowFile}/dispatches`;

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref, inputs }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new GitHubApiError(res.status, `Workflow dispatch failed ${res.status}: ${body}`);
  }
}

export async function fetchLatestPhaseRun(phaseId: PhaseId): Promise<WorkflowRun | null> {
  const config = PHASE_WORKFLOWS[phaseId];
  const data = await githubFetch<{ workflow_runs: WorkflowRun[] }>(
    `/actions/runs?event=workflow_dispatch&per_page=5`,
  );
  const matching = data.workflow_runs?.filter((r) => r.name === config.workflowName);
  return matching?.[0] ?? null;
}

export async function fetchRateLimit(): Promise<{
  limit: number;
  remaining: number;
  reset: number;
}> {
  const token = getToken();
  if (!token) return { limit: 0, remaining: 0, reset: 0 };

  const res = await fetch(`${API_BASE}/rate_limit`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github.v3+json',
    },
  });

  if (!res.ok) return { limit: 0, remaining: 0, reset: 0 };
  const data = await res.json();
  return data.rate;
}
