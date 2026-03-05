import { useState, useEffect } from 'react';
import { githubFetch } from '@/lib/github-client';
import type { GitHubWorkflow, GitHubWorkflowRun, GitHubWorkflowsResponse, GitHubWorkflowRunsResponse } from '@/types/github';
import type { PhaseId } from '@/types/pipeline';

const PHASE_WORKFLOW_NAMES: Record<PhaseId, string> = {
  '01a': '01a-discovery',
  '01b': '01b-subgraph',
  '01e': '01e-properties',
  '02c': '02c-enrich-code',
  '03': '03-audit-map',
  '04': '04-audit-review',
};

export interface WorkflowRunInfo {
  phaseId: PhaseId;
  workflow: GitHubWorkflow | null;
  latestRun: GitHubWorkflowRun | null;
  runs: GitHubWorkflowRun[];
}

export function useWorkflowRuns(branch: string | null): {
  workflows: Record<PhaseId, WorkflowRunInfo>;
  loading: boolean;
  error: string | null;
  refetch: () => void;
} {
  const [workflows, setWorkflows] = useState<Record<PhaseId, WorkflowRunInfo>>(
    {} as Record<PhaseId, WorkflowRunInfo>,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  const refetch = () => setTrigger((n) => n + 1);

  useEffect(() => {
    if (!branch) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        // Fetch all workflows
        const { workflows: allWorkflows } = await githubFetch<GitHubWorkflowsResponse>(
          '/actions/workflows',
        );

        const result: Partial<Record<PhaseId, WorkflowRunInfo>> = {};

        // For each phase, find the matching workflow and its runs
        await Promise.all(
          (Object.entries(PHASE_WORKFLOW_NAMES) as [PhaseId, string][]).map(
            async ([phaseId, workflowName]) => {
              const workflow = allWorkflows.find(
                (w) => w.path.includes(workflowName),
              ) ?? null;

              let runs: GitHubWorkflowRun[] = [];
              if (workflow) {
                try {
                  const data = await githubFetch<GitHubWorkflowRunsResponse>(
                    `/actions/workflows/${workflow.id}/runs?branch=${encodeURIComponent(branch!)}&per_page=5`,
                  );
                  runs = data.workflow_runs;
                } catch {
                  // ignore individual workflow fetch errors
                }
              }

              if (!cancelled) {
                result[phaseId] = {
                  phaseId,
                  workflow,
                  latestRun: runs[0] ?? null,
                  runs,
                };
              }
            },
          ),
        );

        if (!cancelled) {
          setWorkflows(result as Record<PhaseId, WorkflowRunInfo>);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'ワークフローの取得に失敗しました');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [branch, trigger]);

  return { workflows, loading, error, refetch };
}
