import { useState } from 'react';
import { setToken, setRepo, getRepo } from '@/lib/github-client';
import { ja } from '@/i18n/ja';
import styles from './TokenSetup.module.css';

interface Props {
  onConfigured: () => void;
}

export function TokenSetup({ onConfigured }: Props) {
  const [tokenValue, setTokenValue] = useState('');
  const [repoValue, setRepoValue] = useState(getRepo());

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenValue.trim()) {
      setToken(tokenValue.trim());
      if (repoValue.trim()) {
        setRepo(repoValue.trim());
      }
      window.dispatchEvent(new Event('speca-config-changed'));
      onConfigured();
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>{ja.app_title}</h1>
        <p className={styles.desc}>{ja.settings_token_desc}</p>

        <details className={styles.guide}>
          <summary className={styles.guideSummary}>
            トークンの取得方法
          </summary>
          <div className={styles.guideBody}>
            <p className={styles.guideIntro}>
              リポジトリへのアクセス権があれば、所有者でなくてもトークンを作成できます。
              リポジトリとの関係に応じて適切な方式を選んでください。
            </p>

            <h4 className={styles.guideHeading}>
              方法 1: Classic token (推奨)
            </h4>
            <p className={styles.guideHint}>
              共同作業者 (Collaborator) として追加されているリポジトリに使えます。
              所有者でなくても OK。
            </p>
            <ol className={styles.steps}>
              <li>
                <a
                  href="https://github.com/settings/tokens/new"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub {'>'} Settings {'>'} Developer settings {'>'} Tokens (classic)
                </a>
                {' '}を開く
              </li>
              <li>「Note」にトークン名を入力 (例: SPECA Pipeline)</li>
              <li>「Expiration」で有効期限を選択</li>
              <li>
                「Select scopes」で以下にチェック:
                <ul className={styles.permList}>
                  <li><code>repo</code> - リポジトリの読み取り (outputs/ 等)</li>
                  <li><code>workflow</code> - ワークフロー状態の取得 (任意)</li>
                </ul>
              </li>
              <li>「Generate token」をクリックし、表示されたトークンをコピー</li>
            </ol>

            <h4 className={styles.guideHeading}>
              方法 2: Fine-grained token
            </h4>
            <p className={styles.guideHint}>
              自分が所有する or 所属する Organization のリポジトリのみ対象。
              スコープを細かく制御できます。
            </p>
            <ol className={styles.steps}>
              <li>
                <a
                  href="https://github.com/settings/tokens?type=beta"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub {'>'} Settings {'>'} Developer settings {'>'} Fine-grained tokens
                </a>
                {' '}を開く
              </li>
              <li>「Generate new token」をクリック</li>
              <li>トークン名を入力 (例: SPECA Pipeline)</li>
              <li>「Repository access」で対象リポジトリを選択</li>
              <li>
                「Permissions」で以下を有効にする:
                <ul className={styles.permList}>
                  <li><code>Contents</code> - Read-only (outputs/ の読み取り)</li>
                  <li><code>Actions</code> - Read-only (ワークフロー状態の取得)</li>
                  <li><code>Metadata</code> - Read-only (自動で付与)</li>
                </ul>
              </li>
              <li>「Generate token」をクリックし、表示されたトークンをコピー</li>
            </ol>

            <p className={styles.guideNote}>
              トークンはブラウザの localStorage に保存されます。サーバーには送信されません。
            </p>
          </div>
        </details>

        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.field}>
            <span>{ja.settings_token}</span>
            <input
              type="password"
              value={tokenValue}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder={ja.settings_token_placeholder}
              className={styles.input}
              autoFocus
            />
          </label>
          <label className={styles.field}>
            <span>{ja.settings_repo}</span>
            <input
              type="text"
              value={repoValue}
              onChange={(e) => setRepoValue(e.target.value)}
              placeholder="owner/repo"
              className={styles.input}
            />
          </label>
          <button
            type="submit"
            disabled={!tokenValue.trim()}
            className={styles.button}
          >
            {ja.settings_save}
          </button>
        </form>
      </div>
    </div>
  );
}
