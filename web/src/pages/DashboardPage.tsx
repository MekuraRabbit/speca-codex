import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { PipelineFlow } from '@/components/pipeline/PipelineFlow';
import { useGitHubConfig } from '@/hooks/useGitHub';
import { useBranchOverview } from '@/hooks/usePhaseData';
import { useWorkflowRuns } from '@/hooks/useWorkflowRuns';
import styles from './DashboardPage.module.css';

export function DashboardPage() {
  const { branch, setBranch } = useGitHubConfig();
  const { overview, loading, error } = useBranchOverview(branch);
  const { workflows } = useWorkflowRuns(branch);

  return (
    <div>
      <Header
        branch={branch}
        onBranchChange={setBranch}
        title={ja.dashboard_title}
      />
      <div className={styles.content}>
        {!branch && (
          <div className={styles.empty}>{ja.dashboard_no_branch}</div>
        )}

        {branch && loading && (
          <div className={styles.loading}>{ja.loading}</div>
        )}

        {branch && error && (
          <div className={styles.error}>{error}</div>
        )}

        {branch && overview && (
          <>
            {overview.target && (
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>{ja.dashboard_target}</h2>
                <div className={styles.targetInfo}>
                  <div className={styles.targetRow}>
                    <span className={styles.targetLabel}>リポジトリ</span>
                    <span className={styles.targetValue}>{overview.target.target_repo}</span>
                  </div>
                  <div className={styles.targetRow}>
                    <span className={styles.targetLabel}>リファレンス</span>
                    <span className={styles.targetValue}>{overview.target.target_ref_label}</span>
                  </div>
                  <div className={styles.targetRow}>
                    <span className={styles.targetLabel}>コミット</span>
                    <code className={styles.targetCode}>{overview.target.target_commit_short}</code>
                  </div>
                </div>
              </section>
            )}

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>{ja.dashboard_phases}</h2>
              <PipelineFlow
                phaseStatus={overview.phaseStatus}
                workflowRuns={workflows}
              />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
