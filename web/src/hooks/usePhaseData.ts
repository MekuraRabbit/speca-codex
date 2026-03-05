import { useState, useEffect } from 'react';
import { listOutputFiles } from '@/lib/aggregator';
import * as agg from '@/lib/aggregator';
import type { PhaseId, PhaseData } from '@/types/pipeline';

export function usePhaseData(phaseId: PhaseId | null, branch: string | null): {
  data: PhaseData | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
} {
  const [data, setData] = useState<PhaseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  const refetch = () => setTrigger((n) => n + 1);

  useEffect(() => {
    if (!phaseId || !branch) {
      setData(null);
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const files = await listOutputFiles(branch!);
        const result = await agg.fetchPhaseData(phaseId!, branch!, files);
        if (!cancelled) {
          setData(result as PhaseData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'データの取得に失敗しました');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [phaseId, branch, trigger]);

  return { data, loading, error, refetch };
}

export function useBranchOverview(branch: string | null): {
  overview: agg.BranchData | null;
  loading: boolean;
  error: string | null;
} {
  const [overview, setOverview] = useState<agg.BranchData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!branch) {
      setOverview(null);
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const data = await agg.fetchBranchOverview(branch!);
        if (!cancelled) {
          setOverview(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'データの取得に失敗しました');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [branch]);

  return { overview, loading, error };
}
