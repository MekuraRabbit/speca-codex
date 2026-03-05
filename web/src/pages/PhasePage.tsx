import { useParams } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { Header } from '@/components/layout/Header';
import { useGitHubConfig } from '@/hooks/useGitHub';
import { usePhaseData } from '@/hooks/usePhaseData';
import { Phase01aView } from '@/components/phases/Phase01aView';
import { Phase01bView } from '@/components/phases/Phase01bView';
import { Phase01eView } from '@/components/phases/Phase01eView';
import { Phase02cView } from '@/components/phases/Phase02cView';
import { Phase03View } from '@/components/phases/Phase03View';
import { Phase04View } from '@/components/phases/Phase04View';
import type { PhaseId, Phase01aData, Phase01bData, Phase01eData, Phase02cData, Phase03Data, Phase04Data } from '@/types/pipeline';
import styles from './PhasePage.module.css';

const PHASE_TITLES: Record<string, string> = {
  '01a': ja.nav_phase_01a,
  '01b': ja.nav_phase_01b,
  '01e': ja.nav_phase_01e,
  '02c': ja.nav_phase_02c,
  '03': ja.nav_phase_03,
  '04': ja.nav_phase_04,
};

const PHASE_DESCS: Record<string, string> = {
  '01a': ja.phase_01a_desc,
  '01b': ja.phase_01b_desc,
  '01e': ja.phase_01e_desc,
  '02c': ja.phase_02c_desc,
  '03': ja.phase_03_desc,
  '04': ja.phase_04_desc,
};

export function PhasePage() {
  const { phaseId } = useParams<{ phaseId: string }>();
  const { branch, setBranch } = useGitHubConfig();
  const { data, loading, error } = usePhaseData(
    (phaseId as PhaseId) ?? null,
    branch,
  );

  const title = PHASE_TITLES[phaseId ?? ''] ?? phaseId;
  const desc = PHASE_DESCS[phaseId ?? ''] ?? '';

  return (
    <div>
      <Header branch={branch} onBranchChange={setBranch} title={title} />
      <div className={styles.content}>
        <p className={styles.desc}>{desc}</p>

        {!branch && (
          <div className={styles.empty}>{ja.dashboard_no_branch}</div>
        )}
        {branch && loading && (
          <div className={styles.loading}>{ja.loading}</div>
        )}
        {branch && error && (
          <div className={styles.error}>{error}</div>
        )}
        {branch && data && renderPhaseView(phaseId!, data)}
      </div>
    </div>
  );
}

function renderPhaseView(phaseId: string, data: unknown) {
  switch (phaseId) {
    case '01a': return <Phase01aView data={data as Phase01aData} />;
    case '01b': return <Phase01bView data={data as Phase01bData} />;
    case '01e': return <Phase01eView data={data as Phase01eData} />;
    case '02c': return <Phase02cView data={data as Phase02cData} />;
    case '03': return <Phase03View data={data as Phase03Data} />;
    case '04': return <Phase04View data={data as Phase04Data} />;
    default: return <div>{ja.no_data}</div>;
  }
}
