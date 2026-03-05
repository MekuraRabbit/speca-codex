import { Link } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { StatusIndicator, workflowStatus } from '@/components/common/StatusIndicator';
import type { PhaseId } from '@/types/pipeline';
import type { PhaseStatus } from '@/lib/aggregator';
import type { WorkflowRunInfo } from '@/hooks/useWorkflowRuns';
import styles from './PipelineFlow.module.css';

interface PhaseInfo {
  id: PhaseId;
  name: string;
  desc: string;
}

const PHASES: PhaseInfo[] = [
  { id: '01a', name: ja.phase_01a_name, desc: ja.phase_01a_desc },
  { id: '01b', name: ja.phase_01b_name, desc: ja.phase_01b_desc },
  { id: '01e', name: ja.phase_01e_name, desc: ja.phase_01e_desc },
  { id: '02c', name: ja.phase_02c_name, desc: ja.phase_02c_desc },
  { id: '03', name: ja.phase_03_name, desc: ja.phase_03_desc },
  { id: '04', name: ja.phase_04_name, desc: ja.phase_04_desc },
];

interface Props {
  phaseStatus: Record<PhaseId, PhaseStatus>;
  workflowRuns?: Record<PhaseId, WorkflowRunInfo>;
}

export function PipelineFlow({ phaseStatus, workflowRuns }: Props) {
  return (
    <div className={styles.flow}>
      {PHASES.map((phase, i) => {
        const status = phaseStatus[phase.id];
        const wfRun = workflowRuns?.[phase.id];
        const runStatus = wfRun?.latestRun
          ? workflowStatus(wfRun.latestRun.conclusion, wfRun.latestRun.status)
          : status.hasData
            ? 'completed'
            : 'pending';

        return (
          <div key={phase.id} className={styles.phaseWrapper}>
            {i > 0 && <div className={styles.arrow} />}
            <Link to={`/phase/${phase.id}`} className={styles.card}>
              <div className={styles.cardHeader}>
                <span className={styles.phaseId}>{phase.id}</span>
                <StatusIndicator status={runStatus} showLabel={false} />
              </div>
              <div className={styles.phaseName}>{phase.name}</div>
              <div className={styles.phaseDesc}>{phase.desc}</div>
              {status.hasData && (
                <div className={styles.phaseCount}>
                  {status.fileCount} files
                </div>
              )}
            </Link>
          </div>
        );
      })}
    </div>
  );
}
