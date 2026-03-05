import { useState, useEffect } from 'react';
import { githubFetch } from '@/lib/github-client';
import type { GitHubBranch } from '@/types/github';

export function useBranches(): {
  branches: GitHubBranch[];
  loading: boolean;
  error: string | null;
} {
  const [branches, setBranches] = useState<GitHubBranch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // Fetch up to 100 branches, sorted by most recent
        const data = await githubFetch<GitHubBranch[]>(
          '/branches?per_page=100&sort=updated&direction=desc',
        );
        if (!cancelled) {
          setBranches(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'ブランチの取得に失敗しました');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return { branches, loading, error };
}
