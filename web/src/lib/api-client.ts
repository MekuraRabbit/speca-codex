/**
 * Local backend API client for phase dispatch and SSE progress streaming.
 */

export type PhaseId = '01a' | '01b' | '01e' | '02c' | '03' | '04';

const API_BASE = '/api';

export interface PhaseInfo {
  phase_id: string;
  name: string;
  description: string;
  depends_on: string[];
  max_budget_usd: number;
}

export interface RunResponse {
  run_id: string;
  phase_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: number;
  completed_at: number | null;
  error: string | null;
  result: Record<string, unknown> | null;
}

export interface PhaseDispatchRequest {
  phase_id: PhaseId;
  workers?: number;
  max_concurrent?: number;
  force?: boolean;
  keywords?: string;
  spec_urls?: string;
  target_repo?: string;
  target_ref_type?: string;
  audit_scope?: string;
  min_severity?: string;
}

export interface ProgressEvent {
  type: string;
  data: Record<string, unknown>;
}

export async function dispatchPhase(req: PhaseDispatchRequest): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/phases/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Dispatch failed: ${res.status} ${body}`);
  }
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run: ${res.status}`);
  return res.json();
}

export async function cancelRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`);
}

export function subscribeToProgress(
  runId: string,
  onEvent: (event: ProgressEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/runs/${runId}/progress`);

  const eventTypes = [
    'phase_start', 'items_loaded', 'batch_complete',
    'batch_failed', 'cost_update', 'circuit_breaker',
    'phase_complete', 'phase_error', 'done',
  ];

  for (const type of eventTypes) {
    source.addEventListener(type, (e: MessageEvent) => {
      if (type === 'done') {
        onDone();
        source.close();
        return;
      }
      onEvent({ type, data: JSON.parse(e.data) });
    });
  }

  source.onerror = () => {
    onError(new Error('SSE connection lost'));
    source.close();
  };

  return () => source.close();
}
