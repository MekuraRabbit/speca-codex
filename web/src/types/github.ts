export interface GitHubContentItem {
  name: string;
  path: string;
  sha: string;
  size: number;
  url: string;
  html_url: string;
  git_url: string;
  download_url: string | null;
  type: 'file' | 'dir' | 'symlink' | 'submodule';
  content?: string;
  encoding?: string;
}

export interface GitHubBranch {
  name: string;
  commit: {
    sha: string;
    url: string;
  };
  protected: boolean;
}

export interface GitHubWorkflow {
  id: number;
  name: string;
  path: string;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface GitHubWorkflowRun {
  id: number;
  name: string;
  head_branch: string;
  head_sha: string;
  status: 'queued' | 'in_progress' | 'completed' | 'waiting';
  conclusion: 'success' | 'failure' | 'cancelled' | 'skipped' | 'timed_out' | 'action_required' | null;
  workflow_id: number;
  run_number: number;
  created_at: string;
  updated_at: string;
  html_url: string;
  run_started_at: string;
}

export interface GitHubWorkflowRunsResponse {
  total_count: number;
  workflow_runs: GitHubWorkflowRun[];
}

export interface GitHubWorkflowsResponse {
  total_count: number;
  workflows: GitHubWorkflow[];
}

export interface GitHubBranchesResponse extends Array<GitHubBranch> {}

export interface GitHubRateLimit {
  limit: number;
  remaining: number;
  reset: number;
  used: number;
}

export interface GitHubRateLimitResponse {
  resources: {
    core: GitHubRateLimit;
  };
  rate: GitHubRateLimit;
}
