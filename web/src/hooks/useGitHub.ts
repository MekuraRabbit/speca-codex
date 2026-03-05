import { useState, useEffect, useCallback } from 'react';
import { getToken, getRepo } from '@/lib/github-client';

const STORAGE_KEY_BRANCH = 'speca_selected_branch';

export interface GitHubConfig {
  token: string | null;
  repo: string;
  branch: string | null;
  isConfigured: boolean;
}

export function useGitHubConfig(): GitHubConfig & {
  setBranch: (branch: string | null) => void;
} {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [branch, setBranchState] = useState<string | null>(
    localStorage.getItem(STORAGE_KEY_BRANCH),
  );

  const repo = getRepo();
  const isConfigured = token !== null && token.length > 0;

  const setBranch = useCallback((b: string | null) => {
    setBranchState(b);
    if (b) {
      localStorage.setItem(STORAGE_KEY_BRANCH, b);
    } else {
      localStorage.removeItem(STORAGE_KEY_BRANCH);
    }
  }, []);

  // Listen for storage changes (e.g. from settings page)
  useEffect(() => {
    const handler = () => {
      setTokenState(getToken());
    };
    window.addEventListener('storage', handler);
    window.addEventListener('speca-config-changed', handler);
    return () => {
      window.removeEventListener('storage', handler);
      window.removeEventListener('speca-config-changed', handler);
    };
  }, []);

  return { token, repo, branch, isConfigured, setBranch };
}
