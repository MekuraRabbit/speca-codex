import { useState, useEffect } from 'react';
import { ja } from '@/i18n/ja';
import { getToken, setToken, clearToken, getRepo, setRepo, fetchRateLimit } from '@/lib/github-client';
import { Header } from '@/components/layout/Header';
import { useGitHubConfig } from '@/hooks/useGitHub';
import styles from './SettingsPage.module.css';

export function SettingsPage() {
  const { branch, setBranch } = useGitHubConfig();
  const [tokenValue, setTokenValue] = useState(getToken() ?? '');
  const [repoValue, setRepoValue] = useState(getRepo());
  const [saved, setSaved] = useState(false);
  const [rateLimit, setRateLimit] = useState<{ limit: number; remaining: number; reset: number } | null>(null);

  useEffect(() => {
    fetchRateLimit().then(setRateLimit);
  }, [saved]);

  const handleSave = () => {
    setToken(tokenValue.trim());
    setRepo(repoValue.trim());
    window.dispatchEvent(new Event('speca-config-changed'));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClear = () => {
    clearToken();
    setTokenValue('');
    window.dispatchEvent(new Event('speca-config-changed'));
  };

  return (
    <div>
      <Header branch={branch} onBranchChange={setBranch} title={ja.settings_title} />
      <div className={styles.content}>
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{ja.settings_token}</h2>
          <p className={styles.desc}>{ja.settings_token_desc}</p>
          <div className={styles.field}>
            <input
              type="password"
              value={tokenValue}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder={ja.settings_token_placeholder}
              className={styles.input}
            />
          </div>

          <h2 className={styles.sectionTitle}>{ja.settings_repo}</h2>
          <p className={styles.desc}>{ja.settings_repo_desc}</p>
          <div className={styles.field}>
            <input
              type="text"
              value={repoValue}
              onChange={(e) => setRepoValue(e.target.value)}
              placeholder="owner/repo"
              className={styles.input}
            />
          </div>

          <div className={styles.actions}>
            <button onClick={handleSave} className={styles.saveButton}>
              {saved ? ja.settings_saved : ja.settings_save}
            </button>
            <button onClick={handleClear} className={styles.clearButton}>
              {ja.settings_clear}
            </button>
          </div>
        </section>

        {rateLimit && rateLimit.limit > 0 && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>{ja.settings_rate_limit}</h2>
            <div className={styles.rateInfo}>
              <span>{ja.settings_remaining}: {rateLimit.remaining} / {rateLimit.limit}</span>
              <span className={styles.resetTime}>
                リセット: {new Date(rateLimit.reset * 1000).toLocaleTimeString('ja-JP')}
              </span>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
